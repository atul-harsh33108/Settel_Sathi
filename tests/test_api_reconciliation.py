"""Tests for reconciliation REST API endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db.connection import init_db
from app.main import app

client = TestClient(app)


def seed_database_via_api(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api_reconciliation_test.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    init_db(db_url)

    seed_resp = client.post("/api/v1/imports/seed?org_id=org_aarav")
    assert seed_resp.status_code == 200


def test_trigger_reconciliation_run_and_query(tmp_path: Path, monkeypatch) -> None:
    seed_database_via_api(tmp_path, monkeypatch)

    # 1. Trigger reconciliation run via POST
    post_resp = client.post(
        "/api/v1/reconciliation/runs",
        json={"as_of_date": "2026-10-30", "organization_id": "org_aarav"},
        headers={"X-Correlation-ID": "test-rec-corr-001"},
    )
    assert post_resp.status_code == 200
    post_data = post_resp.json()
    assert post_data["status"] == "success"
    assert post_data["correlation_id"] == "test-rec-corr-001"
    assert post_data["total_results"] == 10

    run = post_data["run"]
    assert run["status"] == "COMPLETED"
    assert run["as_of_date"] == "2026-10-30"
    run_id = run["id"]

    summary = post_data["summary"]
    assert summary["total_clusters"] == 10
    assert summary["cases_needed_count"] == 4
    assert summary["total_collected"] == "81450.00"

    # 2. Get specific run via GET /api/v1/reconciliation/runs/{id}
    run_resp = client.get(f"/api/v1/reconciliation/runs/{run_id}?organization_id=org_aarav")
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["id"] == run_id
    assert run_data["status"] == "COMPLETED"

    # 3. List runs via GET /api/v1/reconciliation/runs
    list_runs_resp = client.get("/api/v1/reconciliation/runs?organization_id=org_aarav")
    assert list_runs_resp.status_code == 200
    runs_list = list_runs_resp.json()["runs"]
    assert len(runs_list) >= 1
    assert runs_list[0]["id"] == run_id

    # 4. List all results via GET /api/v1/reconciliation/results
    results_resp = client.get(f"/api/v1/reconciliation/results?run_id={run_id}")
    assert results_resp.status_code == 200
    results_data = results_resp.json()
    assert results_data["count"] == 10
    assert len(results_data["results"]) == 10

    # 5. Filter results by status=UNMATCHED (Hero Demo SCN-02)
    unmatched_resp = client.get(f"/api/v1/reconciliation/results?run_id={run_id}&status=UNMATCHED")
    assert unmatched_resp.status_code == 200
    unmatched_results = unmatched_resp.json()["results"]
    assert len(unmatched_results) == 1
    scn02 = unmatched_results[0]
    assert scn02["scenario_id"] == "SCN-02"
    assert scn02["collected_amount"] == "18450.00"
    assert scn02["bank_credited_amount"] == "0.00"
    assert scn02["case_needed"] is True
    assert scn02["requires_approval"] is True

    # 6. Filter results by case_needed=true
    cases_resp = client.get(f"/api/v1/reconciliation/results?run_id={run_id}&case_needed=true")
    assert cases_resp.status_code == 200
    case_results = cases_resp.json()["results"]
    assert len(case_results) == 4
    case_scenarios = {r["scenario_id"] for r in case_results}
    assert case_scenarios == {"SCN-02", "SCN-04", "SCN-09", "SCN-10"}

    # 7. Get single result detail with full evidence
    result_id = scn02["id"]
    single_res_resp = client.get(f"/api/v1/reconciliation/results/{result_id}")
    assert single_res_resp.status_code == 200
    single_res = single_res_resp.json()
    assert single_res["id"] == result_id
    assert single_res["scenario_id"] == "SCN-02"
    assert "evidence" in single_res
    assert len(single_res["evidence"]["contributing_transaction_ids"]) == 4


def test_api_404_on_missing_run_or_result(tmp_path: Path, monkeypatch) -> None:
    seed_database_via_api(tmp_path, monkeypatch)

    missing_run = client.get("/api/v1/reconciliation/runs/nonexistent_run_id")
    assert missing_run.status_code == 404

    missing_res = client.get("/api/v1/reconciliation/results/nonexistent_res_id")
    assert missing_res.status_code == 404


def test_api_rejects_malformed_as_of_date(tmp_path: Path, monkeypatch) -> None:
    seed_database_via_api(tmp_path, monkeypatch)

    bad_resp = client.post(
        "/api/v1/reconciliation/runs",
        json={"as_of_date": "invalid-date-format"},
    )
    assert bad_resp.status_code == 422
