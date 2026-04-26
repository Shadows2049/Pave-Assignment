# src/tools/base.py
from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(*, max_attempts: int = 3) -> Callable[[F], F]:
    """Run tool; on exception retry up to max_attempts, then return structured error dict."""

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last = e
            return {
                "source": "tool_error",
                "data": None,
                "error": str(last) if last else "unknown",
                "metadata": {"retries": max_attempts, "tool": fn.__name__},
            }

        return wrapper  # type: ignore[return-value]

    return decorator


def ok(
    source: str,
    data: Any,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "data": data,
        "error": None,
        "metadata": metadata or {},
    }


def err(
    source: str,
    message: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "data": None,
        "error": message,
        "metadata": metadata or {},
    }
