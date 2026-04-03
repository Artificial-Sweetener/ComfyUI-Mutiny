"""Normalize runtime failures into safe plugin-facing exceptions."""

from __future__ import annotations

from .models import RuntimeActionContext


class RuntimeAdapterError(RuntimeError):
    """Raise when a runtime action fails with a user-safe message."""


class RuntimeNotReadyError(RuntimeAdapterError):
    """Raise when Mutiny does not reach ready state in time."""


class JobFailedError(RuntimeAdapterError):
    """Raise when a submitted job reaches a failed terminal state."""


def translate_runtime_exception(exc: Exception) -> RuntimeAdapterError:
    """Convert arbitrary exceptions into the plugin's normalized runtime error type."""
    if isinstance(exc, RuntimeAdapterError):
        return exc
    if isinstance(exc, (RuntimeError, ValueError)):
        translated = RuntimeAdapterError(str(exc))
        translated.__cause__ = exc
        return translated
    translated = RuntimeAdapterError("Unexpected runtime error.")
    translated.__cause__ = exc
    return translated


def format_runtime_context(context: RuntimeActionContext) -> str:
    """Render a compact, user-safe context string for runtime logging."""
    return (
        f"node={context.node_name} "
        f"action={context.action_name} "
        f"model={context.model_name or '-'} "
        f"job_id={context.job_id or '-'} "
        f"retry_state={context.retry_state or '-'}"
    )


__all__ = [
    "JobFailedError",
    "RuntimeAdapterError",
    "RuntimeNotReadyError",
    "format_runtime_context",
    "translate_runtime_exception",
]
