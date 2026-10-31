"""Release 0 health and readiness endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.config import Settings, get_settings

router = APIRouter(tags=["system"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
def health(request: Request, settings: SettingsDependency) -> dict[str, str]:
    """Report that the HTTP application is running without exposing configuration."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "correlation_id": request.state.correlation_id,
    }


@router.get("/ready")
def ready(request: Request) -> dict[str, str]:
    """Report that the lightweight Release 0 application is ready to accept work."""

    return {"status": "ready", "correlation_id": request.state.correlation_id}
