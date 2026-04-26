# src/agent/hydration.py
from __future__ import annotations

from typing import Any


def _ok_result(t: dict[str, Any]) -> dict[str, Any] | None:
    r = t.get("result")
    if not isinstance(r, dict) or r.get("error") is not None:
        return None
    return r


def latest_employee_record_from_tasks(tasks: list[dict[str, Any]], before_index: int) -> dict[str, Any] | None:
    """
    Walk completed tasks before `before_index` (newest first) and return one employee dict
    with at least `id`, from the last get_employee or a singleton list_employees result.
    """
    for j in range(before_index - 1, -1, -1):
        if j < 0:
            break
        t = tasks[j]
        if t.get("status") != "complete":
            continue
        tn = t.get("tool_name", "")
        r = _ok_result(t)
        if not r:
            continue
        d = r.get("data")
        if tn == "get_employee" and isinstance(d, dict) and d.get("id"):
            return d
        if tn == "list_employees" and isinstance(d, list) and len(d) == 1:
            row = d[0]
            if isinstance(row, dict) and row.get("id"):
                return row
    return None


def merge_params_from_prior_employee(
    tool_name: str, params: dict[str, Any], emp: dict[str, Any]
) -> dict[str, Any]:
    """
    If the planner left keys empty, fill from the last resolved employee record (chain from get_employee).
    """
    p = dict(params)
    if not emp.get("id"):
        return p

    if tool_name in ("compare_to_market", "check_band_position"):
        raw = p.get("employee_id")
        eid = str(raw).strip() if raw is not None else ""
        if not eid or not eid.startswith("emp-"):
            p["employee_id"] = emp["id"]

    if tool_name == "get_market_benchmarks":
        for key in ("role", "level", "location"):
            if not p.get(key) and emp.get(key) is not None:
                p[key] = emp[key]

    if tool_name == "get_comp_band":
        for key in ("role", "level"):
            if not p.get(key) and emp.get(key) is not None:
                p[key] = emp[key]

    return p
