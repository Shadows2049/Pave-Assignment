# src/tools/market_tools.py
from __future__ import annotations

from src.data.market_data import MarketBenchmark, market_data
from src.tools.base import err, ok, with_retry
from src.tools.scope import is_universal_filter


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
    rows: list[MarketBenchmark] = list(market_data)
    if not is_universal_filter(role):
        r0 = str(role).strip()
        rows = [m for m in rows if m.role == r0]
    if not is_universal_filter(level):
        lv0 = str(level).strip()
        rows = [m for m in rows if m.level == lv0]
    if not is_universal_filter(location):
        loc0 = str(location).strip()
        rows = [m for m in rows if m.location == loc0]
    if component:
        c = str(component).strip()
        rows = [m for m in rows if m.component == c]
    if not rows:
        r_s = "all" if is_universal_filter(role) else str(role).strip()
        lv_s = "all" if is_universal_filter(level) else str(level).strip()
        loc_s = "all" if is_universal_filter(location) else str(location).strip()
        return err(
            "market_data",
            f"No market benchmarks for {r_s} / {lv_s} / {loc_s}"
            + (f" / component {component}" if component else ""),
            metadata={"role": r_s, "level": lv_s, "location": loc_s},
        )
    return ok(
        "market_data",
        [_ser(m) for m in rows],
        metadata={"dataset": "market_data.py", "count": len(rows)},
    )
