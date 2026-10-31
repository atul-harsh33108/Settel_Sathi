"""API endpoints for fixture seeding, file upload, job status, and import summaries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app.db.connection import get_connection, init_db
from app.services import repository
from app.services.importer import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB limit


@router.post("/seed")
def seed_fixtures(request: Request, org_id: str = "org_aarav") -> dict[str, Any]:
    """Seed the database with certified synthetic v1 fixtures offline."""
    init_db()

    # Search candidates for v1 fixtures
    candidate_paths = [
        Path("serv_data/fixtures/v1"),
        Path("fixtures/synthetic/v1"),
    ]
    target_dir: Path | None = None
    for p in candidate_paths:
        if (p / "manifest.json").exists():
            target_dir = p
            break

    if not target_dir:
        raise HTTPException(
            status_code=404,
            detail="Synthetic fixture directory with manifest.json not found",
        )

    service = ImportService()
    try:
        jobs = service.import_bundle(target_dir, organization_id=org_id)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to seed bundle: {exc}",
        ) from exc

    conn = get_connection()
    try:
        counts = repository.get_financial_counts(conn, org_id)
    finally:
        conn.close()

    return {
        "status": "completed",
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "fixture_dir": str(target_dir),
        "jobs": [j.to_dict() for j in jobs],
        "record_counts": counts,
    }


@router.post("/upload")
async def upload_fixture(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    source_type: Annotated[str | None, Form()] = None,
    org_id: Annotated[str, Form()] = "org_aarav",
) -> dict[str, Any]:
    """Upload and validate an individual financial fixture CSV or JSON file."""
    init_db()

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds maximum allowed size (10 MB)")

    service = ImportService()
    job = service.import_file(
        content=content,
        file_name=file.filename or "upload.csv",
        source_type=source_type,
        organization_id=org_id,
    )

    response_payload = job.to_dict()
    if job.errors_json:
        response_payload["errors"] = json.loads(job.errors_json)

    status_code = 400 if job.status == "FAILED" else 200
    if status_code == 400:
        raise HTTPException(status_code=400, detail=response_payload)

    return {
        "status": "success",
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "job": response_payload,
    }


@router.get("/summary")
def get_summary(request: Request, org_id: str = "org_aarav") -> dict[str, Any]:
    """Get current database record counts and provenance summary."""
    init_db()
    conn = get_connection()
    try:
        counts = repository.get_financial_counts(conn, org_id)
        artifacts = repository.list_source_artifacts(conn, org_id, limit=10)
    finally:
        conn.close()

    return {
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "organization_id": org_id,
        "dataset_version": "v1",
        "schema_version": "1.0",
        "record_counts": counts,
        "artifacts_count": len(artifacts),
        "recent_artifacts": [a.to_dict() for a in artifacts],
    }


@router.get("/jobs")
def list_jobs(request: Request, org_id: str = "org_aarav", limit: int = 50) -> dict[str, Any]:
    """List recent import job executions."""
    init_db()
    conn = get_connection()
    try:
        jobs = repository.list_import_jobs(conn, org_id, limit=limit)
    finally:
        conn.close()

    return {
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "jobs": [j.to_dict() for j in jobs],
    }


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    """Fetch status and detailed errors for a specific import job."""
    init_db()
    conn = get_connection()
    try:
        job = repository.find_job_by_id(conn, job_id)
    finally:
        conn.close()

    if not job:
        raise HTTPException(status_code=404, detail=f"Import job '{job_id}' not found")

    res = job.to_dict()
    if job.errors_json:
        res["errors"] = json.loads(job.errors_json)

    return {
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "job": res,
    }


@router.get("/artifacts")
def list_artifacts(request: Request, org_id: str = "org_aarav", limit: int = 50) -> dict[str, Any]:
    """List ingested source artifacts and checksum provenance."""
    init_db()
    conn = get_connection()
    try:
        artifacts = repository.list_source_artifacts(conn, org_id, limit=limit)
    finally:
        conn.close()

    return {
        "correlation_id": getattr(request.state, "correlation_id", ""),
        "artifacts": [a.to_dict() for a in artifacts],
    }
