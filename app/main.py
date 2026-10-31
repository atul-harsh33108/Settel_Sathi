"""SettleSaathi FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.api.routes import router as system_router
from app.api.routes_import import router as import_router
from app.api.routes_reconciliation import router as reconciliation_router
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize process-level configuration without creating data implicitly."""

    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("application_started environment=%s", settings.environment)
    yield
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Build the API application so tests and Uvicorn share identical configuration."""

    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=None,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Correlation-ID"],
    )

    @application.middleware("http")
    async def correlation_id_middleware(request: Request, call_next) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
        request.state.correlation_id = correlation_id[:128]
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response

    application.include_router(system_router)
    application.include_router(system_router, prefix=settings.api_prefix)
    application.include_router(import_router, prefix=settings.api_prefix)
    application.include_router(reconciliation_router, prefix=settings.api_prefix)
    return application


app = create_app()
