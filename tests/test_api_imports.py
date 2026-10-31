"""Tests for import API endpoints."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.connection import init_db
from app.main import app

client = TestClient(app)
FIXTURES_DIR = Path("fixtures/synthetic/v1")


def test_api_seed_and_summary(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api_test.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    init_db(db_url)

    # 1. Trigger Seed
    resp = client.post(
        "/api/v1/imports/seed?org_id=org_aarav",
        headers={"X-Correlation-ID": "test-seed-123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["correlation_id"] == "test-seed-123"
    assert data["record_counts"]["transactions"] == 20
    assert data["record_counts"]["settlements"] == 11
    assert len(data["jobs"]) == 5

    # 2. Query Summary
    sum_resp = client.get("/api/v1/imports/summary?org_id=org_aarav")
    assert sum_resp.status_code == 200
    sum_data = sum_resp.json()
    assert sum_data["record_counts"]["transactions"] == 20
    assert sum_data["artifacts_count"] == 5

    # 3. List Jobs
    jobs_resp = client.get("/api/v1/imports/jobs?org_id=org_aarav")
    assert jobs_resp.status_code == 200
    assert len(jobs_resp.json()["jobs"]) >= 5

    # 4. Check Single Job
    job_id = data["jobs"][0]["id"]
    single_resp = client.get(f"/api/v1/imports/jobs/{job_id}")
    assert single_resp.status_code == 200
    assert single_resp.json()["job"]["id"] == job_id

    # 5. List Artifacts
    arts_resp = client.get("/api/v1/imports/artifacts?org_id=org_aarav")
    assert arts_resp.status_code == 200
    assert len(arts_resp.json()["artifacts"]) == 5


def test_api_upload_invalid_csv_returns_400(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api_upload_err.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    init_db(db_url)

    bad_content = b"invalid,header\n1,2\n"
    file_tuple = ("bad.csv", io.BytesIO(bad_content), "text/csv")

    resp = client.post(
        "/api/v1/imports/upload",
        files={"file": file_tuple},
        data={"source_type": "TRANSACTIONS", "org_id": "org_aarav"},
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert detail["status"] == "FAILED"
    assert detail["error_count"] > 0


def test_api_job_not_found_returns_404(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api_job_404.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    init_db(db_url)

    resp = client.get("/api/v1/imports/jobs/job_ghost_999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]


def test_api_upload_valid_csv_returns_200(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api_upload_ok.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("SETTLESAATHI_DATABASE_URL", db_url)
    init_db(db_url)

    valid_bank = FIXTURES_DIR / "bank_statement.csv"
    file_tuple = ("bank_statement.csv", io.BytesIO(valid_bank.read_bytes()), "text/csv")

    resp = client.post(
        "/api/v1/imports/upload",
        files={"file": file_tuple},
        data={"source_type": "BANK_STATEMENT", "org_id": "org_aarav"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["job"]["status"] == "COMPLETED"
    assert data["job"]["processed_records"] == 6
