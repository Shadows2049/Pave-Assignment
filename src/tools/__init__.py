# src/tools/__init__.py
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.tools.band_tools import get_comp_band
from src.tools.employee_tools import get_employee, list_employees
from src.tools.market_tools import get_market_benchmarks
from src.tools.analysis_tools import analyze_team, check_band_position, compare_to_market

# Callable registry: tool_name -> function
TOOL_REGISTRY: dict[str, Callable[..., dict[str, Any]]] = {
    "get_employee": get_employee,
    "list_employees": list_employees,
    "get_market_benchmarks": get_market_benchmarks,
    "get_comp_band": get_comp_band,
    "compare_to_market": compare_to_market,
    "check_band_position": check_band_position,
    "analyze_team": analyze_team,
}

TOOL_LIST_DESCRIPTION: str = """
Available tools (call by exact name; params are keyword-only):

- get_employee(name: str) -> employee record (employees)
- list_employees(department?, role?, level?, location?) -> list (employees)
- get_market_benchmarks(role, level, location, component?) -> benchmarks (market_data)
- get_comp_band(role, level, component?) -> internal bands (comp_bands)
- compare_to_market(employee_id, component="total_comp") -> vs market p50 etc (market_data)
- check_band_position(employee_id, component="total_comp") -> vs band (comp_bands)
- analyze_team(department, analysis_type) -> one of: attrition_risk, pay_equity, market_gap (mixed)

Pass employee_id (e.g. emp-001) when a tool needs it, after resolving name with get_employee if needed.
For a single named employee, always pair market comparison with check_band_position so the answer includes internal policy range (comp_bands) and external benchmarks (market_data).
""".strip()
