# src/tools/band_tools.py
from __future__ import annotations

from src.data.comp_bands import CompBand, comp_bands
from src.tools.base import err, ok, with_retry


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
    r, lv = role.strip(), level.strip()
    rows = [b for b in comp_bands if b.role == r and b.level == lv]
    if component:
        c = component.strip()
        rows = [b for b in rows if b.component == c]
    if not rows:
        return err("comp_bands", f"No comp band for {r} / {lv}" + (f" / {component}" if component else ""))
    return ok("comp_bands", [_ser(b) for b in rows], metadata={"dataset": "comp_bands.py"})
