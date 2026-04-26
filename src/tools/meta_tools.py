# src/tools/meta_tools.py
"""Non-data tools: scope and policy (no access to comp fixtures)."""
from __future__ import annotations

from src.tools.base import ok, with_retry


@with_retry(max_attempts=3)
def decline_unrelated_query(*, user_query: str = "") -> dict:
    """
    Use when the user's question is not about compensation, employees, or HR pay data
    in this system. Returns a fixed policy message; does not read employees/market/bands.
    """
    u = (user_query or "").strip()
    return ok(
        "agent_policy",
        {
            "message": (
                "I'm Paige, a compensation analyst for this workspace. I can only help with "
                "questions that use our people, market benchmark, and internal band data—e.g. "
                "pay vs market, comp bands, team or department comp views, and named employee lookups. "
                "This question is outside that scope, so I can't use our tools to answer it."
            ),
        },
        metadata={"out_of_scope": True, "user_query_echo": u[:500]},
    )
