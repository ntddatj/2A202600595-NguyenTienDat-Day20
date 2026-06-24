"""Tracing hooks with LangSmith integration."""

import logging
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter
from typing import Any

logger = logging.getLogger(__name__)


def configure_tracing() -> str | None:
    """Enable LangSmith tracing if LANGSMITH_API_KEY is set.

    LangGraph calls are traced automatically once these env vars are present.
    Returns the project name that was activated, or None if tracing is disabled.
    """
    from multi_agent_research_lab.core.config import get_settings

    settings = get_settings()
    if not settings.langsmith_api_key:
        logger.info("LangSmith tracing disabled (no LANGSMITH_API_KEY).")
        return None

    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langsmith_api_key)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langsmith_project)
    logger.info("LangSmith tracing enabled → project=%s", settings.langsmith_project)
    return settings.langsmith_project


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Context manager that wraps a code block in a timed span.

    When LangSmith is configured, also emits a RunTree span so the call
    appears nested inside the active LangGraph trace.
    """
    started = perf_counter()
    span: dict[str, Any] = {"name": name, "attributes": attributes or {}, "duration_seconds": None}

    langsmith_run = None
    try:
        if os.environ.get("LANGCHAIN_TRACING_V2") == "true":
            from langsmith import Client

            client = Client()
            langsmith_run = client.create_run(
                name=name,
                run_type="chain",
                inputs=attributes or {},
            )
    except Exception:
        pass  # tracing is best-effort, never block the main flow

    try:
        yield span
    finally:
        span["duration_seconds"] = perf_counter() - started
        if langsmith_run is not None:
            try:
                from langsmith import Client

                Client().update_run(langsmith_run.id, outputs={"duration_seconds": span["duration_seconds"]})
            except Exception:
                pass
