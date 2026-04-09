"""Langfuse SDK initialization and wrapper.

Provides a singleton Langfuse client.  When credentials are missing the
module exposes a no-op stub so the simulation can run without Langfuse.
"""

from __future__ import annotations

import logging
from typing import Any

from src.config import LANGFUSE_ENABLED, LANGFUSE_HOST, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY

logger = logging.getLogger(__name__)

_client: Any = None  # langfuse.Langfuse | None


def get_langfuse() -> Any:
    """Return the Langfuse client singleton (or *None* if not configured)."""
    global _client
    if _client is not None:
        return _client

    if not LANGFUSE_ENABLED:
        logger.info("Langfuse credentials not set — instrumentation disabled.")
        return None

    try:
        from langfuse import Langfuse

        _client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        logger.info("Langfuse client initialised (host=%s).", LANGFUSE_HOST)
        return _client
    except Exception:
        logger.warning("Failed to initialise Langfuse — continuing without it.", exc_info=True)
        return None


def flush() -> None:
    """Flush any pending Langfuse events."""
    if _client is not None:
        try:
            _client.flush()
        except Exception:
            logger.warning("Langfuse flush failed.", exc_info=True)
