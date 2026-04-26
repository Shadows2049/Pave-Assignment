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
