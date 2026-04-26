# src/tools/analysis_tools.py
from __future__ import annotations

from collections import defaultdict
from src.data.employees import employees
from src.data.comp_bands import comp_bands
from src.data.market_data import market_data
from src.tools.base import err, ok, with_retry
from src.tools.employee_tools import _serial


def _by_id(eid: str):
    eid = eid.strip()
    for e in employees:
        if e.id == eid:
            return e
    return None


def _market_row(role: str, level: str, location: str, component: str):
    for m in market_data:
        if m.role == role and m.level == level and m.location == location and m.component == component:
            return m
    return None


def _band_row(role: str, level: str, component: str):
    for b in comp_bands:
        if b.role == role and b.level == level and b.component == component:
            return b
    return None


def _bracket_against(value: int, p25: int, p50: int, p75: int, p90: int) -> str:
    if value < p25:
        return f"below_p25 (value {value:,} < p25 {p25:,})"
    if value < p50:
        return f"p25_to_p50"
    if value < p75:
        return f"p50_to_p75"
    if value < p90:
        return f"p75_to_p90"
    return f"above_p90"


@with_retry(max_attempts=3)
def compare_to_market(
    *,
    employee_id: str,
    component: str = "total_comp",
) -> dict:
    """Compare an employee's comp component to market percentiles (same role/level/location)."""
    e = _by_id(employee_id)
    if not e:
        return err("employees", f"Unknown employee_id: {employee_id}")
    c = component.strip() if component else "total_comp"
    val = getattr(e.comp, c) if c in ("base", "equity", "bonus", "total_comp") else e.comp.total_comp
    m = _market_row(e.role, e.level, e.location, c)
    if not m:
        return err(
            "market_data",
            f"No {c!r} market data for {e.role} / {e.level} / {e.location}.",
            metadata={"employee_id": employee_id, "employee_name": e.name},
        )
    tag = _bracket_against(val, m.p25, m.p50, m.p75, m.p90)
    verdict = "competitive" if val >= m.p50 else "below_market_median" if val < m.p50 else "at_or_above_median"
    if val < m.p25:
        verdict = "below_p25_susceptible"
    return ok(
        "market_data",
        {
            "employee": _serial(e),
            "value": val,
            "component": c,
            "market": {
                "p25": m.p25,
                "p50": m.p50,
                "p75": m.p75,
                "p90": m.p90,
                "sample_size": m.sample_size,
            },
            "bracket": tag,
            "verdict": verdict,
        },
        metadata={"dataset": "employees.py + market_data.py"},
    )


@with_retry(max_attempts=3)
def check_band_position(
    *,
    employee_id: str,
    component: str = "total_comp",
) -> dict:
    """Check employee pay vs internal comp band (national, no location)."""
    e = _by_id(employee_id)
    if not e:
        return err("employees", f"Unknown employee_id: {employee_id}")
    c = component.strip() if component else "total_comp"
    val = getattr(e.comp, c) if c in ("base", "equity", "bonus", "total_comp") else e.comp.total_comp
    b = _band_row(e.role, e.level, c)
    if not b:
        return err("comp_bands", f"No {c!r} band for {e.role} / {e.level}.", metadata={"employee_id": e.id})
    pos = "below_min" if val < b.min else "above_max" if val > b.max else "in_band"
    dist_mid = val - b.mid
    return ok(
        "comp_bands",
        {
            "employee": _serial(e),
            "value": val,
            "component": c,
            "band": {"min": b.min, "mid": b.mid, "max": b.max, "updated_at": b.updated_at},
            "position": pos,
            "delta_from_mid": dist_mid,
        },
        metadata={"dataset": "employees.py + comp_bands.py"},
    )


@with_retry(max_attempts=3)
def analyze_team(
    *,
    department: str,
    analysis_type: str,
) -> dict:
    """
    analysis_type: one of
      - attrition_risk: rank employees in dept by (market vs pay) and performance
      - pay_equity: flag same-role/level comp spread by gender
      - market_gap: aggregate gap vs market p50 (total_comp) for dept
    """
    dept = department.strip()
    at = analysis_type.strip().lower().replace(" ", "_")
    team = [e for e in employees if e.department.lower() == dept.lower()]

    if not team:
        return err("employees", f"No employees in department {department!r}", metadata={})

    if at == "attrition_risk":
        rows = []
        for e in team:
            m = _market_row(e.role, e.level, e.location, "total_comp")
            if m:
                ratio = e.comp.total_comp / m.p50 if m.p50 else None
                risk = 0.0
                if ratio and ratio < 0.9 and e.performance.rating in ("exceeds", "exceptional"):
                    risk = 0.8
                elif ratio and ratio < 1.0 and e.performance.rating in ("exceeds", "exceptional", "meets"):
                    risk = 0.4
                if ratio and ratio < 0.85:
                    risk = max(risk, 0.5)
            else:
                ratio, risk = None, 0.1
            rows.append(
                {
                    "employee": e.name,
                    "id": e.id,
                    "total_comp": e.comp.total_comp,
                    "performance": e.performance.rating,
                    "vs_market_p50_ratio": ratio,
                    "attrition_risk_score": risk,
                    "note": "no total_comp market" if m is None else None,
                }
            )
        rows.sort(key=lambda x: -x["attrition_risk_score"])
        return ok(
            "analysis",
            {"department": dept, "ranked": rows},
            metadata={"analysis_type": "attrition_risk", "dataset": "employees + market_data"},
        )

    if at in ("pay_equity", "equity"):
        # Same role+level+location groups
        by_key: dict[tuple, list] = defaultdict(list)
        for e in team:
            by_key[(e.role, e.level, e.location)].append(e)
        issues = []
        for key, g in by_key.items():
            if len(g) < 2:
                continue
            by_gender: dict[str, list] = defaultdict(list)
            for e in g:
                by_gender[e.demographics.gender].append(e.comp.total_comp)
            for gend, vals in by_gender.items():
                if len(vals) < 1:
                    continue
            genders = list(by_gender.keys())
            for i in range(len(genders)):
                for j in range(i + 1, len(genders)):
                    ga, gb = genders[i], genders[j]
                    a_avg = sum(by_gender[ga]) / len(by_gender[ga])
                    b_avg = sum(by_gender[gb]) / len(by_gender[gb])
                    if a_avg and b_avg and abs(a_avg - b_avg) / max(a_avg, b_avg) > 0.1:
                        issues.append(
                            {
                                "role": key[0],
                                "level": key[1],
                                "location": key[2],
                                "avg_total_comp": {ga: a_avg, gb: b_avg},
                                "spread_pct": abs(a_avg - b_avg) / max(a_avg, b_avg) * 100,
                            }
                        )
        return ok(
            "analysis",
            {
                "department": dept,
                "groups": len(by_key),
                "potential_gaps": issues,
                "caveat": "Descriptive only; not statistical significance testing.",
            },
            metadata={"analysis_type": "pay_equity", "dataset": "employees"},
        )

    if at in ("market_gap", "dept_market_gap", "internal_vs_market"):
        gaps = []
        for e in team:
            m = _market_row(e.role, e.level, e.location, "total_comp")
            if not m:
                gaps.append(
                    {
                        "employee": e.name,
                        "id": e.id,
                        "gap_vs_p50": None,
                        "note": "no market data",
                    }
                )
            else:
                g = e.comp.total_comp - m.p50
                gaps.append(
                    {
                        "employee": e.name,
                        "id": e.id,
                        "total_comp": e.comp.total_comp,
                        "market_p50": m.p50,
                        "gap_vs_p50": g,
                    }
                )
        # aggregate by sub-department: average gap for those with data
        valid = [x for x in gaps if x.get("gap_vs_p50") is not None]
        avg_gap = sum(x["gap_vs_p50"] for x in valid) / len(valid) if valid else None
        return ok(
            "analysis",
            {
                "department": dept,
                "average_gap_vs_market_p50": avg_gap,
                "per_employee": gaps,
            },
            metadata={"analysis_type": "market_gap", "dataset": "employees + market_data"},
        )

    return err("analysis", f"Unknown analysis_type: {analysis_type!r}. Use attrition_risk, pay_equity, or market_gap.")
