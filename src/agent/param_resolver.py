# src/agent/param_resolver.py
"""
Generic LLM step: full keyword args for the *current* tool from user intent + prior tool outputs.
New tools: add to TOOL_REGISTRY; introspection provides the param schema to the model.
"""
from __future__ import annotations

import inspect
import json
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agent.supervisor import DEFAULT_MODEL
from src.tools import TOOL_REGISTRY


def _tool_kw_names(tool_name: str) -> set[str]:
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        return set()
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return set()
    out: set[str] = set()
    for pname, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        out.add(pname)
    return out


def _tool_schema_block(tool_name: str) -> str:
    """Human-readable schema for the LLM."""
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        return "(unknown tool)"
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return "(no signature)"
    parts: list[str] = []
    for pname, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL):
            continue
        default = p.default
        d = "" if default is inspect.Parameter.empty else f" = {default!r}"
        parts.append(f"  {pname}{d}")
    return f"{tool_name}(\n" + "\n".join(parts) + "\n)" if parts else f"{tool_name}()"


def _as_plain_result(obj: Any) -> Any:
    try:
        return json.loads(json.dumps(obj, default=str))
    except (TypeError, ValueError):
        return str(obj)[:8000]


def build_prior_steps_for_prompt(tasks: list[dict[str, Any]], before_index: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for j in range(before_index):
        tj = tasks[j]
        if tj.get("status") != "complete":
            continue
        entry: dict[str, Any] = {
            "task_id": tj.get("task_id"),
            "tool_name": tj.get("tool_name"),
            "params": tj.get("params"),
        }
        r = tj.get("result")
        if r is not None:
            try:
                entry["result"] = _as_plain_result(r)
            except Exception:
                entry["result"] = str(r)[:8000]
        out.append(entry)
    return out


def _filter_to_tool_params(tool_name: str, d: dict[str, Any]) -> dict[str, Any]:
    """Drop keys the tool does not accept (avoids TypeError from an over-eager model)."""
    names = _tool_kw_names(tool_name)
    if not names:
        return d
    return {k: v for k, v in d.items() if k in names}


class _ResolvedOut(BaseModel):
    params_json: str = Field(
        default="{}",
        description="Single JSON object: keyword arguments for this tool only.",
    )


class _PlanNormEntry(BaseModel):
    task_id: str = Field(..., description="Same task_id as the input plan step")
    params_json: str = Field(
        default="{}",
        description="Minified JSON object: valid keyword args for this tool's signature",
    )


class _PlanNormOut(BaseModel):
    rows: list[_PlanNormEntry] = Field(
        ...,
        description="Exactly one entry per plan step, same order as the input list",
    )


def normalize_plan_drafts(
    *,
    plan_steps: list[dict[str, Any]],
    user_query: str,
    main_objective: str,
    supervisor_context: str,
    model: str | None = None,
    config: RunnableConfig | None = None,
) -> list[dict[str, Any]]:
    """
    For each plan step, ask the model to map draft fields to valid tool kwargs
    (names + types) using introspected signatures. Called from the supervisor
    so execution receives parameters that already match each tool.
    `plan_steps`: each has task_id, tool_name, params (dict), context (str).
    Returns: list of param dicts in the same order as plan_steps.
    """
    if not plan_steps:
        return []
    for it in plan_steps:
        it.setdefault("params", {})
        it.setdefault("context", "")

    # One schema block per tool name (deduped) to keep the prompt small.
    unique_tools: list[str] = []
    seen: set[str] = set()
    for it in plan_steps:
        t = str(it.get("tool_name") or "")
        if t and t not in seen and t in TOOL_REGISTRY:
            seen.add(t)
            unique_tools.append(t)
    tool_docs = "\n\n".join(
        f"### {name}\n{_tool_schema_block(name)}" for name in unique_tools
    )
    if not tool_docs.strip():
        tool_docs = "No valid tools; pass params through as-is where possible."

    items_json = json.dumps(
        [
            {
                "task_id": it.get("task_id"),
                "tool_name": it.get("tool_name"),
                "draft": it.get("params") or {},
                "context": it.get("context") or "",
            }
            for it in plan_steps
        ],
        indent=2,
        default=str,
    )

    llm = ChatOpenAI(model=model or DEFAULT_MODEL, temperature=0)
    structured = llm.with_structured_output(_PlanNormOut, method="function_calling")
    system = f"""You normalize **draft** tool parameters from a planner into **valid** keyword arguments.

Each tool is a Python function. You must only use parameter **names** that appear in the signature
blocks below, with JSON-serializable values. Drop unknown keys. Fill required fields from the
user question, supervisor objective, and each step's context when the draft is empty or wrong.

**Resolving natural language to parameters**
- "all departments" / "company-wide" / "everyone" → for tools that have optional filters, use the
  documented all-company values (e.g. `department: "all"` for analyze_team, or omit optional filters
  for list_employees when the intent is the full roster if the signature allows).
- get_employee: use a single clear name string; no employee_id in this tool.
- compare_to_market / check_band_position: use `employee_id` like "emp-001" if the user already gave it; otherwise you may use {{}} and leave resolution to a later run step if a prior get_employee will supply it.
- get_market_benchmarks: `role`, `level`, and `location` are required; use "all" (or a single location) per tool behavior for location/role/level if the user asked for the entire matrix.
- get_comp_band: `role` and `level` required in many cases; never pass `location`.
- analyze_team: `analysis_type` is required; `department` optional — use a specific department name or "all" for all departments.
- decline_unrelated_query: pass `user_query` with the user's message (or a short paraphrase) for traceability; no fixture fields.
- If you cannot fill a required field, put the best partial object you can; never invent people or ids not implied by the user.

**Tool signatures**
{tool_docs}
""".strip()
    human = f"""User question: {user_query!r}

Main objective: {main_objective!r}

Supervisor plan context: {supervisor_context!r}

Plan steps to normalize (output **rows** in the same order, one `params_json` per step):
{items_json}
""".strip()
    out_rows: _PlanNormOut | None = None
    try:
        out_rows = structured.invoke(
            [SystemMessage(content=system), HumanMessage(content=human)],
            config=config,
        )
    except Exception:
        return [dict(it.get("params") or {}) for it in plan_steps]

    if not out_rows or not out_rows.rows:
        return [dict(it.get("params") or {}) for it in plan_steps]

    def _parse_row(ent: _PlanNormEntry) -> dict[str, Any] | None:
        raw = (ent.params_json or "{}").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
        try:
            parsed = json.loads(raw)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        return parsed

    by_task: dict[str, dict[str, Any]] = {}
    for ent in out_rows.rows:
        tid = str(ent.task_id or "").strip()
        if not tid:
            continue
        parsed = _parse_row(ent)
        if parsed is None:
            continue
        tname = next((str(p.get("tool_name") or "") for p in plan_steps if str(p.get("task_id") or "") == tid), None)
        if tname and tname in TOOL_REGISTRY:
            by_task[tid] = _filter_to_tool_params(tname, parsed)
        else:
            by_task[tid] = parsed

    result: list[dict[str, Any]] = []
    rows = out_rows.rows
    for i, it in enumerate(plan_steps):
        tid = str(it.get("task_id") or "").strip()
        tname = str(it.get("tool_name") or "")
        original = dict(it.get("params") or {})
        if tid in by_task:
            result.append(by_task[tid])
            continue
        if i < len(rows) and len(rows) == len(plan_steps):
            parsed = _parse_row(rows[i])
            if parsed is not None and tname in TOOL_REGISTRY:
                result.append(_filter_to_tool_params(tname, parsed))
            elif parsed is not None:
                result.append(parsed)
            else:
                result.append(original)
        else:
            result.append(original)
    return result


def resolve_tool_params(
    *,
    tool_name: str,
    draft_params: dict[str, Any],
    tasks: list[dict[str, Any]],
    current_index: int,
    user_query: str,
    task_note: str,
    supervisor_context: str,
    model: str | None = None,
    config: RunnableConfig | None = None,
) -> dict[str, Any]:
    """
    Returns keyword args to pass to the tool. On failure, returns copy of draft_params.
    Executor may still run hydration as a safety net.
    """
    draft = dict(draft_params)
    if tool_name not in TOOL_REGISTRY:
        return draft

    prior = build_prior_steps_for_prompt(tasks, current_index)
    prior_str = json.dumps(prior, indent=2, default=str)
    if len(prior_str) > 24_000:
        prior_str = prior_str[:24_000] + "\n... (truncated)"

    schema = _tool_schema_block(tool_name)
    llm = ChatOpenAI(model=model or DEFAULT_MODEL, temperature=0)
    structured = llm.with_structured_output(_ResolvedOut, method="function_calling")
    system = f"""You output keyword arguments for exactly ONE tool call, as JSON in params_json.

Tool signature (use only these parameter names; values must be JSON-serializable):
{schema}

Rules:
- Copy correct values from the draft when they are already valid.
- If prior steps include an employee with field "id" (e.g. emp-001), use that id in compare_to_market, check_band_position.
- get_market_benchmarks: needs role, level, location — take from a prior get_employee "result"."data" or nested employee fields when missing in draft.
- get_comp_band: needs role, level, optional component — never use "location" for this tool.
- Do not add keys that are not in the signature.
""".strip()
    human = f"""User question: {user_query!r}

Supervisor / plan context: {supervisor_context!r}

This step note: {task_note!r}

Draft params: {json.dumps(draft, default=str)}

Prior completed steps (in order); use their results to fill missing required fields:
{prior_str}

Return params_json: full kwargs object for {tool_name!r} only.
""".strip()
    try:
        out: _ResolvedOut = structured.invoke(
            [SystemMessage(content=system), HumanMessage(content=human)],
            config=config,
        )
        raw = (out.params_json or "{}").strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1]
            if "```" in raw:
                raw = raw.rsplit("```", 1)[0]
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return draft
        cleaned = _filter_to_tool_params(tool_name, parsed)
        return cleaned
    except Exception:
        return draft
