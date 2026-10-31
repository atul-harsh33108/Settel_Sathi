"""API endpoints for deterministic reconciliation runs, results, and evidence packages."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.db.connection import get_connection
from app.services import repository
from app.services.reconciliation import ReconciliationService

router = APIRouter(prefix="/reconciliation", tags=["Reconciliation"])


class ReconcileRequest(BaseModel):
    as_of_date: str = Field(
        default="2026-10-30",
        description="Fixed as-of date (YYYY-MM-DD) for evaluation",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    organization_id: str = Field(
        default="org_aarav",
        description="Tenant / Organization ID",
    )


@router.post("/runs")
def trigger_reconciliation(
    request: Request,
    payload: ReconcileRequest | None = None,
) -> dict[str, Any]:
    """Trigger a deterministic reconciliation run across all ingested financial records."""
    req_body = payload or ReconcileRequest()
    service = ReconciliationService()

    try:
        run_record, results = service.reconcile(
            organization_id=req_body.organization_id,
            as_of_date=req_body.as_of_date,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Reconciliation run failed: {exc}",
        ) from exc

    return {
        "status": "success",
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "run": run_record.to_dict(),
        "summary": json.loads(run_record.summary_counts_json or "{}"),
        "total_results": len(results),
    }


@router.get("/runs")
def list_runs(
    organization_id: str = "org_aarav",
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """List historical reconciliation runs."""
    conn = get_connection()
    try:
        runs = repository.list_reconciliation_runs(conn, organization_id, limit=limit)
    finally:
        conn.close()

    return {
        "organization_id": organization_id,
        "runs": [
            {
                **r.to_dict(),
                "summary": json.loads(r.summary_counts_json or "{}"),
            }
            for r in runs
        ],
    }


@router.get("/runs/{run_id}")
def get_run(
    run_id: str,
    organization_id: str = "org_aarav",
) -> dict[str, Any]:
    """Retrieve status and metrics for a specific reconciliation run."""
    conn = get_connection()
    try:
        run = repository.find_run_by_id(conn, run_id, organization_id)
    finally:
        conn.close()

    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return {
        **run.to_dict(),
        "summary": json.loads(run.summary_counts_json or "{}"),
    }


@router.get("/results")
def list_results(
    run_id: str | None = None,
    organization_id: str = "org_aarav",
    status: str | None = None,
    scenario_id: str | None = None,
    case_needed: bool | None = None,
) -> dict[str, Any]:
    """List reconciliation results, defaulting to the latest run if run_id is omitted."""
    conn = get_connection()
    try:
        target_run_id = run_id
        if not target_run_id:
            latest = repository.find_latest_run(conn, organization_id)
            if latest:
                target_run_id = latest.id

        results = repository.list_reconciliation_results(
            conn,
            organization_id=organization_id,
            run_id=target_run_id,
            status=status,
            scenario_id=scenario_id,
            case_needed=case_needed,
        )
    finally:
        conn.close()

    formatted_results = []
    for r in results:
        d = r.to_dict()
        d["evidence"] = json.loads(r.evidence_json)
        d["input_record_ids"] = json.loads(r.input_record_ids_json)
        d["matched_record_ids"] = json.loads(r.matched_record_ids_json)
        formatted_results.append(d)

    return {
        "organization_id": organization_id,
        "run_id": target_run_id,
        "count": len(formatted_results),
        "results": formatted_results,
    }


@router.get("/results/{result_id}")
def get_result(
    result_id: str,
    organization_id: str = "org_aarav",
) -> dict[str, Any]:
    """Retrieve full evidence package and details for a specific reconciliation result."""
    conn = get_connection()
    try:
        res = repository.find_result_by_id(conn, result_id, organization_id)
    finally:
        conn.close()

    if not res:
        raise HTTPException(status_code=404, detail=f"Result '{result_id}' not found")

    d = res.to_dict()
    d["evidence"] = json.loads(res.evidence_json)
    d["input_record_ids"] = json.loads(res.input_record_ids_json)
    d["matched_record_ids"] = json.loads(res.matched_record_ids_json)
    return d
