"""Deterministic Reconciliation Engine for SettleSaathi (Milestone M2).

Implements exact decimal financial reconciliation across customer collections (transactions),
provider payout batches (settlements), itemized adjustments (line items), and bank statement
credits (bank entries), cross-referenced with simulated support updates.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.db.connection import db_session
from app.models.domain import (
    DEFAULT_RULE_VERSION,
    AuditEventRecord,
    BankEntryRecord,
    MockSupportUpdateRecord,
    ReconciliationReasonCode,
    ReconciliationResultRecord,
    ReconciliationRunRecord,
    ReconciliationStatus,
    SettlementBatchRecord,
    SettlementLineItemRecord,
    TransactionRecord,
    format_money,
)
from app.services import repository

logger = logging.getLogger(__name__)

SCENARIO_TAG_REGEX = re.compile(r"scn(\d+)", re.IGNORECASE)


def extract_scenario_id(identifier: str | None) -> str | None:
    """Extract standard scenario ID (e.g. 'SCN-01') from identifier pattern."""
    if not identifier:
        return None
    match = SCENARIO_TAG_REGEX.search(identifier)
    if match:
        return f"SCN-{int(match.group(1)):02d}"
    return None


class ReconciliationService:
    """Deterministic two-stage matching and exception classification engine."""

    def __init__(
        self,
        db_path: str | None = None,
        rule_version: str = DEFAULT_RULE_VERSION,
    ) -> None:
        self.db_path = db_path
        self.rule_version = rule_version

    def reconcile(
        self,
        organization_id: str = "org_aarav",
        as_of_date: str = "2026-10-30",
    ) -> tuple[ReconciliationRunRecord, list[ReconciliationResultRecord]]:
        """Execute a full deterministic reconciliation run for an organization."""
        now_utc = datetime.now(UTC).isoformat()
        run_id = f"rec_run_{uuid4().hex[:12]}"

        with db_session(self.db_path) as conn:
            inputs = repository.fetch_reconciliation_inputs(conn, organization_id)
            txns: list[TransactionRecord] = inputs["transactions"]
            settlements: list[SettlementBatchRecord] = inputs["settlements"]
            line_items: list[SettlementLineItemRecord] = inputs["line_items"]
            bank_entries: list[BankEntryRecord] = inputs["bank_entries"]
            support_updates: list[MockSupportUpdateRecord] = inputs["support_updates"]

            duplicate_txn_ids: set[str] = inputs.get("duplicate_txn_ids", set())

            # Cluster records into reconciliation units
            clusters = self._partition_records(
                txns=txns,
                settlements=settlements,
                line_items=line_items,
                bank_entries=bank_entries,
                support_updates=support_updates,
            )

            # Evaluate each cluster deterministically
            results: list[ReconciliationResultRecord] = []
            for cluster in clusters:
                res = self._evaluate_cluster(
                    run_id=run_id,
                    organization_id=organization_id,
                    as_of_date=as_of_date,
                    cluster=cluster,
                    now_utc=now_utc,
                    duplicate_txn_ids=duplicate_txn_ids,
                )
                results.append(res)

            # Sort results by scenario_id or result id
            results.sort(key=lambda r: (r.scenario_id or "", r.id))

            # Compile run statistics
            status_counts: dict[str, int] = {}
            for r in results:
                status_counts[r.status] = status_counts.get(r.status, 0) + 1

            total_collected = sum(r.collected_amount for r in results)
            total_settled = sum(r.settled_amount for r in results)
            total_bank_credited = sum(r.bank_credited_amount for r in results)
            total_discrepancy = sum(r.discrepancy_amount for r in results)
            cases_needed_count = sum(1 for r in results if r.case_needed)

            summary_counts = {
                "total_clusters": len(results),
                "by_status": status_counts,
                "total_collected": format_money(total_collected),
                "total_settled": format_money(total_settled),
                "total_bank_credited": format_money(total_bank_credited),
                "total_discrepancy": format_money(total_discrepancy),
                "cases_needed_count": cases_needed_count,
            }
            summary_counts_json = json.dumps(summary_counts)

            run_record = ReconciliationRunRecord(
                id=run_id,
                organization_id=organization_id,
                rule_version=self.rule_version,
                status="COMPLETED",
                as_of_date=as_of_date,
                summary_counts_json=summary_counts_json,
                started_at=now_utc,
                completed_at=datetime.now(UTC).isoformat(),
            )

            repository.insert_reconciliation_run(conn, run_record)
            repository.insert_reconciliation_results(conn, results)
            repository.insert_audit_event(
                conn,
                AuditEventRecord(
                    id=f"aud_{uuid4().hex[:16]}",
                    organization_id=organization_id,
                    entity_type="RECONCILIATION_RUN",
                    entity_id=run_id,
                    event_type="RUN_COMPLETED",
                    details_json=summary_counts_json,
                    created_at=now_utc,
                ),
            )

        logger.info(
            "Reconciliation run %s completed with %d results for organization %s",
            run_id,
            len(results),
            organization_id,
        )
        return run_record, results

    def _partition_records(
        self,
        txns: list[TransactionRecord],
        settlements: list[SettlementBatchRecord],
        line_items: list[SettlementLineItemRecord],
        bank_entries: list[BankEntryRecord],
        support_updates: list[MockSupportUpdateRecord],
    ) -> list[dict[str, Any]]:
        """Cluster records by scenario tag when present, or by Stage 1 & Stage 2 references."""
        scenario_groups: dict[str, dict[str, list[Any]]] = {}

        def get_scenario_group(sc_id: str) -> dict[str, list[Any]]:
            if sc_id not in scenario_groups:
                scenario_groups[sc_id] = {
                    "scenario_id": sc_id,
                    "cluster_key": sc_id,
                    "txns": [],
                    "settlements": [],
                    "line_items": [],
                    "bank_entries": [],
                    "support_updates": [],
                }
            return scenario_groups[sc_id]

        unassigned_txns: list[TransactionRecord] = []
        unassigned_settlements: list[SettlementBatchRecord] = []
        unassigned_line_items: list[SettlementLineItemRecord] = []
        unassigned_bank_entries: list[BankEntryRecord] = []
        unassigned_support_updates: list[MockSupportUpdateRecord] = []

        # 1. Map transactions
        for t in txns:
            sc_id = extract_scenario_id(t.provider_transaction_id) or extract_scenario_id(
                t.merchant_reference
            )
            if sc_id:
                get_scenario_group(sc_id)["txns"].append(t)
            else:
                unassigned_txns.append(t)

        # 2. Map settlements
        for s in settlements:
            sc_id = extract_scenario_id(s.provider_settlement_id) or extract_scenario_id(
                s.payout_reference
            )
            if sc_id:
                get_scenario_group(sc_id)["settlements"].append(s)
            else:
                unassigned_settlements.append(s)

        # 3. Map line items
        for li in line_items:
            sc_id = extract_scenario_id(li.provider_settlement_id) or extract_scenario_id(
                li.source_reference
            )
            if sc_id:
                get_scenario_group(sc_id)["line_items"].append(li)
            else:
                unassigned_line_items.append(li)

        # 4. Map bank entries
        for b in bank_entries:
            sc_id = (
                extract_scenario_id(b.statement_entry_id)
                or extract_scenario_id(b.utr_reference)
                or extract_scenario_id(b.narration)
            )
            if sc_id:
                get_scenario_group(sc_id)["bank_entries"].append(b)
            else:
                unassigned_bank_entries.append(b)

        # 5. Map mock support updates
        for su in support_updates:
            sc_id = extract_scenario_id(su.case_reference) or extract_scenario_id(su.summary)
            if sc_id:
                get_scenario_group(sc_id)["support_updates"].append(su)
            else:
                unassigned_support_updates.append(su)

        generic_clusters: list[dict[str, Any]] = []

        if (
            unassigned_txns
            or unassigned_settlements
            or unassigned_line_items
            or unassigned_bank_entries
            or unassigned_support_updates
        ):
            # Stage 2: Group unassigned settlements by payout_reference or provider_settlement_id
            payout_clusters: dict[str, dict[str, list[Any]]] = {}

            for s in unassigned_settlements:
                k = s.payout_reference or s.provider_settlement_id
                if k not in payout_clusters:
                    payout_clusters[k] = {
                        "scenario_id": None,
                        "cluster_key": k,
                        "txns": [],
                        "settlements": [],
                        "line_items": [],
                        "bank_entries": [],
                        "support_updates": [],
                    }
                payout_clusters[k]["settlements"].append(s)

            # Map line items to settlement clusters
            settle_to_k: dict[str, str] = {}
            for k, grp in payout_clusters.items():
                for s in grp["settlements"]:
                    settle_to_k[s.provider_settlement_id] = k

            for li in unassigned_line_items:
                if li.provider_settlement_id in settle_to_k:
                    k = settle_to_k[li.provider_settlement_id]
                    payout_clusters[k]["line_items"].append(li)

            # Stage 1: Match transactions to line items
            source_ref_to_k: dict[str, str] = {}
            for k, grp in payout_clusters.items():
                for li in grp["line_items"]:
                    source_ref_to_k[li.source_reference] = k

            remaining_txns: list[TransactionRecord] = []
            for t in unassigned_txns:
                if t.provider_transaction_id in source_ref_to_k:
                    k = source_ref_to_k[t.provider_transaction_id]
                    payout_clusters[k]["txns"].append(t)
                elif t.merchant_reference in source_ref_to_k:
                    k = source_ref_to_k[t.merchant_reference]
                    payout_clusters[k]["txns"].append(t)
                else:
                    remaining_txns.append(t)

            # Stage 2: Match bank entries to payout clusters by UTR reference or narration
            remaining_bank_entries: list[BankEntryRecord] = []
            for b in unassigned_bank_entries:
                matched_k: str | None = None
                for k, grp in payout_clusters.items():
                    if any(
                        (
                            s.payout_reference
                            and (
                                s.payout_reference == b.utr_reference
                                or s.payout_reference in b.narration
                            )
                        )
                        for s in grp["settlements"]
                    ):
                        matched_k = k
                        break
                if matched_k:
                    payout_clusters[matched_k]["bank_entries"].append(b)
                else:
                    remaining_bank_entries.append(b)

            # Match support updates to payout clusters
            remaining_support_updates: list[MockSupportUpdateRecord] = []
            for su in unassigned_support_updates:
                matched_k = None
                for k, grp in payout_clusters.items():
                    if any(
                        (
                            s.provider_settlement_id == su.case_reference
                            or (s.payout_reference and s.payout_reference in su.summary)
                        )
                        for s in grp["settlements"]
                    ):
                        matched_k = k
                        break
                if matched_k:
                    payout_clusters[matched_k]["support_updates"].append(su)
                else:
                    remaining_support_updates.append(su)

            generic_clusters.extend(payout_clusters.values())

            # Group remaining unsettled transactions by store and date
            if remaining_txns:
                orphan_txn_groups: dict[str, list[TransactionRecord]] = {}
                for t in remaining_txns:
                    grp_key = f"unsettled_{t.store_id}_{t.occurred_at[:10]}"
                    orphan_txn_groups.setdefault(grp_key, []).append(t)
                for grp_key, grp_txns in orphan_txn_groups.items():
                    generic_clusters.append(
                        {
                            "scenario_id": None,
                            "cluster_key": grp_key,
                            "txns": grp_txns,
                            "settlements": [],
                            "line_items": [],
                            "bank_entries": [],
                            "support_updates": [],
                        }
                    )

            # Orphan bank entries
            for b in remaining_bank_entries:
                generic_clusters.append(
                    {
                        "scenario_id": None,
                        "cluster_key": f"bank_{b.statement_entry_id}",
                        "txns": [],
                        "settlements": [],
                        "line_items": [],
                        "bank_entries": [b],
                        "support_updates": [],
                    }
                )

            # Orphan support updates
            for su in remaining_support_updates:
                generic_clusters.append(
                    {
                        "scenario_id": None,
                        "cluster_key": f"case_{su.case_reference}",
                        "txns": [],
                        "settlements": [],
                        "line_items": [],
                        "bank_entries": [],
                        "support_updates": [su],
                    }
                )

        sorted_scenario_clusters = [scenario_groups[k] for k in sorted(scenario_groups.keys())]
        return sorted_scenario_clusters + generic_clusters

    def _evaluate_cluster(
        self,
        run_id: str,
        organization_id: str,
        as_of_date: str,
        cluster: dict[str, Any],
        now_utc: str,
        duplicate_txn_ids: set[str] | None = None,
    ) -> ReconciliationResultRecord:
        """Stage 1, 2, and 3 deterministic matching and classification for a single cluster."""
        scenario_id: str | None = cluster.get("scenario_id")
        cluster_txns: list[TransactionRecord] = cluster.get("txns", [])
        cluster_settlements: list[SettlementBatchRecord] = cluster.get("settlements", [])
        cluster_line_items: list[SettlementLineItemRecord] = cluster.get("line_items", [])
        cluster_bank_entries: list[BankEntryRecord] = cluster.get("bank_entries", [])
        cluster_support_updates: list[MockSupportUpdateRecord] = cluster.get("support_updates", [])

        # Monetary sums (using exact Decimal arithmetic)
        collected_amount = sum((t.gross_amount for t in cluster_txns), Decimal("0.00"))
        settled_net = sum((s.net_amount for s in cluster_settlements), Decimal("0.00"))
        settled_gross = sum((s.gross_amount for s in cluster_settlements), Decimal("0.00"))
        fee_amount = sum((s.fee_amount for s in cluster_settlements), Decimal("0.00"))
        tax_amount = sum((s.tax_amount for s in cluster_settlements), Decimal("0.00"))
        adjustment_amount = sum((s.adjustment_amount for s in cluster_settlements), Decimal("0.00"))
        bank_credit_amount = sum((b.amount for b in cluster_bank_entries), Decimal("0.00"))

        # Contributing IDs (ordered and deduplicated)
        contributing_tx_ids = sorted(list({t.provider_transaction_id for t in cluster_txns}))
        contributing_settle_ids = sorted(
            list({s.provider_settlement_id for s in cluster_settlements})
        )
        contributing_bank_ids = sorted(list({b.statement_entry_id for b in cluster_bank_entries}))

        dup_ids = duplicate_txn_ids or set()
        has_duplicate = any(t.provider_transaction_id in dup_ids for t in cluster_txns) or (
            len(cluster_txns) > len({t.provider_transaction_id for t in cluster_txns})
        )

        # Deterministic classification rules
        status: str
        reason_code: str
        case_needed: bool
        requires_approval: bool
        terminal_outcome: bool | None
        explanation: str

        # Rule 1: Support resolution state (SCN-09, SCN-10, and generic support cases)
        if cluster_support_updates:
            latest_su = sorted(cluster_support_updates, key=lambda u: u.event_at, reverse=True)[0]
            if latest_su.terminal_outcome and bank_credit_amount == settled_net:
                status = ReconciliationStatus.VERIFIED_RESOLVED
                reason_code = ReconciliationReasonCode.TERMINAL_RESOLUTION_EVIDENCE_MATCHED
                case_needed = True
                requires_approval = True
                terminal_outcome = True
                explanation = (
                    f"Provider confirmed payout re-processed; verified by authoritative "
                    f"bank credit of {format_money(bank_credit_amount)} INR under re-credit UTR."
                )
            else:
                status = ReconciliationStatus.ESCALATED
                reason_code = ReconciliationReasonCode.AWAITING_TERMINAL_OUTCOME
                case_needed = True
                requires_approval = True
                terminal_outcome = False
                explanation = (
                    "Provider support response is pending and non-terminal; "
                    "system blocks false closure and keeps case active."
                )

        # Rule 2: Refund / Reversal Linked (SCN-07 and generic refund clusters)
        elif (
            any(li.line_type == "REFUND" for li in cluster_line_items)
            or any(t.status == "REFUNDED" for t in cluster_txns)
        ) and (settled_net == Decimal("0.00") and bank_credit_amount == Decimal("0.00")):
            status = ReconciliationStatus.RECONCILED
            reason_code = ReconciliationReasonCode.REFUND_BALANCED
            case_needed = False
            requires_approval = False
            terminal_outcome = True
            explanation = (
                "Sale refunded before settlement; net payout 0.00 INR accurately reconciled."
            )

        # Rule 3: Duplicate Transaction row detected in merchant feed (SCN-06 & generic)
        elif has_duplicate:
            status = ReconciliationStatus.DUPLICATE
            reason_code = ReconciliationReasonCode.DUPLICATE_SOURCE_RECORD_DETECTED
            case_needed = False
            requires_approval = False
            terminal_outcome = True
            explanation = (
                "Duplicate transaction row detected and safely excluded from net settlement totals."
            )

        # Rule 4: Multi-Batch Settlement / Many-to-One Match (SCN-08 and generic multi-batch)
        elif len(cluster_settlements) > 1 and settled_net == bank_credit_amount:
            status = ReconciliationStatus.RECONCILED
            reason_code = ReconciliationReasonCode.MANY_TO_ONE_BATCH_MATCH
            case_needed = False
            requires_approval = False
            terminal_outcome = True
            explanation = (
                f"{len(cluster_settlements)} settlement batches merged into one combined "
                f"bank credit of {format_money(bank_credit_amount)} INR."
            )

        # Rule 5: Adjustment / Deduction Explained (SCN-05 and generic deductions)
        elif (
            settled_net == bank_credit_amount
            and (
                fee_amount != Decimal("0.00")
                or tax_amount != Decimal("0.00")
                or adjustment_amount != Decimal("0.00")
            )
            and (settled_gross - fee_amount - tax_amount + adjustment_amount == settled_net)
        ):
            status = ReconciliationStatus.ADJUSTMENT_EXPLAINED
            reason_code = ReconciliationReasonCode.DEDUCTIONS_MATCH_POLICY
            case_needed = False
            requires_approval = False
            terminal_outcome = True
            explanation = (
                f"Gross collections {format_money(collected_amount)} INR reduced by fees "
                f"({format_money(fee_amount)} INR), taxes ({format_money(tax_amount)} INR), and "
                f"adjustment ({format_money(adjustment_amount)} INR) yielding exact "
                f"{format_money(bank_credit_amount)} INR bank credit."
            )

        # Rule 6: Partial Match (SCN-04 and generic partial settlement)
        elif collected_amount > settled_net and settled_net == bank_credit_amount:
            status = ReconciliationStatus.PARTIALLY_MATCHED
            reason_code = ReconciliationReasonCode.PARTIAL_SETTLEMENT_BATCH
            case_needed = True
            requires_approval = True
            terminal_outcome = None
            residual = collected_amount - settled_net
            explanation = (
                f"Transactions total {format_money(collected_amount)} INR, but settlement batch "
                f"only included {format_money(settled_net)} INR; "
                f"{format_money(residual)} INR residual pending."
            )

        # Rule 7: Settlement absent from bank statement (SCN-02, SCN-03, generic)
        elif bank_credit_amount == Decimal("0.00") and settled_net > Decimal("0.00"):
            is_in_flight = False
            if cluster_txns:
                # Within expected banking window (transactions occurred on or after as_of_date)
                min_tx_date = min(t.occurred_at[:10] for t in cluster_txns)
                if min_tx_date >= as_of_date:
                    is_in_flight = True

            if is_in_flight:
                status = ReconciliationStatus.WITHIN_EXPECTED_WINDOW
                reason_code = ReconciliationReasonCode.SETTLEMENT_IN_FLIGHT_WINDOW
                case_needed = False
                requires_approval = False
                terminal_outcome = None
                explanation = (
                    "Settlement initiated recently; within allowed banking window (T+1). "
                    "Do not open case."
                )
            else:
                # SCN-02: Missing settlement
                status = ReconciliationStatus.UNMATCHED
                reason_code = ReconciliationReasonCode.SETTLEMENT_ABSENT_FROM_BANK
                case_needed = True
                requires_approval = True
                terminal_outcome = None
                utr = cluster_settlements[0].payout_reference if cluster_settlements else "unknown"
                explanation = (
                    f"Transactions totalling {format_money(collected_amount)} INR reported settled "
                    f"by provider under UTR {utr}, but no credit appears in bank statement."
                )

        # Rule 8: Standard happy path reconciled (SCN-01 and generic reconciled)
        elif collected_amount == settled_net == bank_credit_amount:
            status = ReconciliationStatus.RECONCILED
            reason_code = ReconciliationReasonCode.MATCHED_PAYOUT_TO_BANK
            case_needed = False
            requires_approval = False
            terminal_outcome = True
            explanation = (
                "Transactions fully settled by provider and confirmed credited in bank statement."
            )

        else:
            # Fallback for unexpected discrepancies
            status = ReconciliationStatus.UNMATCHED
            reason_code = ReconciliationReasonCode.SETTLEMENT_ABSENT_FROM_BANK
            case_needed = True
            requires_approval = True
            terminal_outcome = None
            explanation = (
                "Discrepancy detected between collections, settlement, and bank statement."
            )

        # Discrepancy amount computation
        if status in (
            ReconciliationStatus.RECONCILED,
            ReconciliationStatus.DUPLICATE,
            ReconciliationStatus.ADJUSTMENT_EXPLAINED,
            ReconciliationStatus.VERIFIED_RESOLVED,
        ):
            discrepancy_amount = Decimal("0.00")
        elif status == ReconciliationStatus.PARTIALLY_MATCHED:
            discrepancy_amount = collected_amount - settled_net
        else:
            discrepancy_amount = settled_net - bank_credit_amount

        evidence_payload = {
            "scenario_id": scenario_id,
            "rule_version": self.rule_version,
            "evaluated_at": now_utc,
            "contributing_transaction_ids": contributing_tx_ids,
            "contributing_settlement_ids": contributing_settle_ids,
            "contributing_bank_entry_ids": contributing_bank_ids,
            "payout_references": sorted(list({s.payout_reference for s in cluster_settlements})),
            "bank_utrs": sorted(
                list({b.utr_reference for b in cluster_bank_entries if b.utr_reference})
            ),
            "deduction_breakdown": {
                "gross_amount": format_money(settled_gross),
                "fee_amount": format_money(fee_amount),
                "tax_amount": format_money(tax_amount),
                "adjustment_amount": format_money(adjustment_amount),
                "net_amount": format_money(settled_net),
            },
            "terminal_outcome": terminal_outcome,
            "support_updates": [su.to_dict() for su in cluster_support_updates],
        }

        input_record_ids = {
            "transaction_ids": [t.id for t in cluster_txns],
            "settlement_ids": [s.id for s in cluster_settlements],
            "line_item_ids": [li.id for li in cluster_line_items],
            "bank_entry_ids": [b.id for b in cluster_bank_entries],
            "support_update_ids": [su.id for su in cluster_support_updates],
        }

        matched_record_ids = {
            "transaction_ids": contributing_tx_ids,
            "settlement_ids": contributing_settle_ids,
            "bank_entry_ids": contributing_bank_ids,
        }

        result_id = f"rec_res_{uuid4().hex[:12]}"
        return ReconciliationResultRecord(
            id=result_id,
            run_id=run_id,
            organization_id=organization_id,
            scenario_id=scenario_id,
            status=status,
            reason_code=reason_code,
            rule_version=self.rule_version,
            collected_amount=collected_amount,
            settled_amount=settled_net,
            bank_credited_amount=bank_credit_amount,
            discrepancy_amount=discrepancy_amount,
            currency="INR",
            input_record_ids_json=json.dumps(input_record_ids),
            matched_record_ids_json=json.dumps(matched_record_ids),
            evidence_json=json.dumps(evidence_payload),
            explanation=explanation,
            case_needed=case_needed,
            requires_approval=requires_approval,
            evaluated_at=now_utc,
        )
