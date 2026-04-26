# src/tools/band_tools.py
from __future__ import annotations

from src.data.comp_bands import CompBand, comp_bands
from src.tools.base import err, ok, with_retry
from src.tools.scope import is_universal_filter


def _ser(b: CompBand) -> dict:
    return {
        "role": b.role,
        "level": b.level,
        "component": b.component,
        "min": b.min,
        "mid": b.mid,
        "max": b.max,
        "updated_at": b.updated_at,
    }


@with_retry(max_attempts=3)
def get_comp_band(
    *,
    role: str,
    level: str,
    component: str | None = None,
) -> dict:
    """Internal comp bands (national) for role+level. Optional component filter."""
    rows: list[CompBand] = list(comp_bands)
    if not is_universal_filter(role):
        r0 = str(role).strip()
        rows = [b for b in rows if b.role == r0]
    if not is_universal_filter(level):
        lv0 = str(level).strip()
        rows = [b for b in rows if b.level == lv0]
    if component:
        c = str(component).strip()
        rows = [b for b in rows if b.component == c]
    if not rows:
        r_s = "all" if is_universal_filter(role) else str(role).strip()
        lv_s = "all" if is_universal_filter(level) else str(level).strip()
        return err("comp_bands", f"No comp band for {r_s} / {lv_s}" + (f" / {component}" if component else ""))
    return ok("comp_bands", [_ser(b) for b in rows], metadata={"dataset": "comp_bands.py"})
