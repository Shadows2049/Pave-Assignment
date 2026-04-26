# src/tools/scope.py
"""Resolve tokens like "all" / "company" to company-wide (no filter) in tools."""
from __future__ import annotations

_UNIVERSAL: frozenset[str] = frozenset(
    {
        "all",
        "any",
        "every",
        "everyone",
        "entire",
        "company",
        "organization",
        "org",
        "global",
        "whole company",
        "all company",
        "n/a",
        "na",
        "none",
        "anywhere",
        "all departments",
        "all depts",
        "all roles",
        "all levels",
        "all locations",
        "all locs",
        "all cities",
        "all offices",
        "all_departments",
        "all_depts",
        "all_roles",
        "all_levels",
        "all_locations",
        "all_locs",
        "*",
        "-",
    }
)


def _norm(s: str) -> str:
    return " ".join(s.split()).lower()


def is_universal_filter(value: str | None) -> bool:
    """
    True = do not narrow on this field (all values / company-wide).
    None or empty = no filter; explicit "all" / "company" / … = same.
    """
    if value is None:
        return True
    s = str(value)
    if not s.strip():
        return True
    n = _norm(s)
    if n in _UNIVERSAL:
        return True
    if n.startswith("all ") and len(n) > 4:
        return True
    return False
