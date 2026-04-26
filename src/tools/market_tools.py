# src/tools/market_tools.py
from __future__ import annotations

from src.data.market_data import MarketBenchmark, market_data
from src.tools.base import err, ok, with_retry


def _ser(m: MarketBenchmark) -> dict:
    return {
        "role": m.role,
        "level": m.level,
        "location": m.location,
        "component": m.component,
        "p25": m.p25,
        "p50": m.p50,
        "p75": m.p75,
        "p90": m.p90,
        "sample_size": m.sample_size,
        "updated_at": m.updated_at,
    }


@with_retry(max_attempts=3)
def get_market_benchmarks(
    *,
    role: str,
    level: str,
    location: str,
    component: str | None = None,
) -> dict:
    """
    Return market percentiles for role+level+location.
    If component is None, return all available components.
    """
    r, lv, loc = role.strip(), level.strip(), location.strip()
    rows = [
        m
        for m in market_data
        if m.role == r and m.level == lv and m.location == loc
    ]
    if component:
        c = component.strip()
        rows = [m for m in rows if m.component == c]
    if not rows:
        return err(
            "market_data",
            f"No market benchmarks for {r} / {lv} / {loc}"
            + (f" / component {component}" if component else ""),
            metadata={"role": r, "level": lv, "location": loc},
        )
    return ok(
        "market_data",
        [_ser(m) for m in rows],
        metadata={"dataset": "market_data.py", "count": len(rows)},
    )
