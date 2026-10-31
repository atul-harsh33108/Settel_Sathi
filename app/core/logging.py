"""Structured logging helpers with correlation IDs."""

from __future__ import annotations

import logging


def configure_logging(level: str) -> None:
    """Configure concise, process-wide logging once at API startup."""

    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
