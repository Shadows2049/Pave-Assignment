# src/tools/employee_tools.py
from __future__ import annotations

from src.data.employees import Employee, employees
from src.tools.base import err, ok, with_retry


def _serial(e: Employee) -> dict:
    return {
        "id": e.id,
        "name": e.name,
        "department": e.department,
        "role": e.role,
        "level": e.level,
        "location": e.location,
        "manager": e.manager,
        "start_date": e.start_date,
        "comp": {
            "base": e.comp.base,
            "equity": e.comp.equity,
            "bonus": e.comp.bonus,
            "total_comp": e.comp.total_comp,
        },
        "performance": {
            "rating": e.performance.rating,
            "last_review_date": e.performance.last_review_date,
            "summary": e.performance.summary,
        },
        "demographics": {
            "gender": e.demographics.gender,
            "ethnicity": e.demographics.ethnicity,
        },
    }


@with_retry(max_attempts=3)
def get_employee(*, name: str) -> dict:
    """Look up a single employee by name (fuzzy: case-insensitive substring on full name)."""
    name_l = name.strip().lower()
    matches: list[Employee] = [e for e in employees if name_l in e.name.lower() or e.name.lower() == name_l]
    if not matches:
        return err("employees", f"No employee found matching: {name!r}", metadata={"query": name})
    if len(matches) > 1:
        return err(
            "employees",
            f"Multiple matches: {[m.name for m in matches]}. Be more specific.",
            metadata={"matches": [m.name for m in matches]},
        )
    return ok("employees", _serial(matches[0]), metadata={"dataset": "employees.py"})


@with_retry(max_attempts=3)
def list_employees(
    *,
    department: str | None = None,
    role: str | None = None,
    level: str | None = None,
    location: str | None = None,
) -> dict:
    """Filter employees. Any argument omitted means no filter on that field."""
    out: list[Employee] = list(employees)
    if department:
        d = department.strip().lower()
        out = [e for e in out if e.department.lower() == d]
    if role:
        r = role.strip()
        out = [e for e in out if r.lower() in e.role.lower()]
    if level:
        lv = level.strip()
        out = [e for e in out if e.level == lv]
    if location:
        loc = location.strip()
        out = [e for e in out if e.location == loc]
    return ok(
        "employees",
        [_serial(e) for e in out],
        metadata={"dataset": "employees.py", "count": len(out)},
    )
