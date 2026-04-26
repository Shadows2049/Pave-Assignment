# src/agent/supervisor.py
from __future__ import annotations

import json
import uuid
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agent.state import AgentState, TaskState
from src.tools import TOOL_LIST_DESCRIPTION, TOOL_REGISTRY

DEFAULT_MODEL = "gpt-4.1-mini"
# Imported after DEFAULT_MODEL to avoid import cycles (param_resolver imports DEFAULT_MODEL).
from src.agent.param_resolver import normalize_plan_drafts


class PlanTaskOut(BaseModel):
    task_id: str = Field(..., description="Unique id within the plan, e.g. t1, t2")
    tool_name: str = Field(..., description="Exact key from the tool list")
    # Use JSON string to satisfy strict structured output schema (no open dicts)
    params_json: str = Field(default="{}", description="JSON string of keyword args for the tool")
    context: str = Field(..., description="One-line note of why this tool runs")


class SupervisorPlan(BaseModel):
    main_objective: str
    context: str = Field(..., description="Condensed user intent and constraints")
    tasks: list[PlanTaskOut] = Field(
        min_length=1, description="Ordered steps. First steps often resolve name -> employee_id"
    )


def _build_model(*, model: str | None) -> ChatOpenAI:
    return ChatOpenAI(model=model or DEFAULT_MODEL, temperature=0)


def supervisor_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    plan_id = str(uuid.uuid4())[:8]
    llm = _build_model(model=state.get("model"))
    structured = llm.with_structured_output(SupervisorPlan, method="function_calling")

    tools_allowed = "\n".join(f"- {k}" for k in sorted(TOOL_REGISTRY))
    system = f"""You are a compensation analysis planner. Your only job is to route questions to tools that read our fixture comp data, OR to decline when the user is not asking about that domain.

{TOOL_LIST_DESCRIPTION}

Valid tool_name values (exactly):
{tools_allowed}

In-scope topics: employee pay, market benchmarks, comp bands, team/department comp analysis, named people, attrition/market-gap/pay-equity *as supported by the tools*.

**Out of scope (do not call get_employee, list_employees, market, band, or analyze_team for these):** weather, news, general knowledge, coding help, math homework, company policies you cannot answer from the fixtures, or anything unrelated to compensation data. For those, plan a **single** task: `decline_unrelated_query` with params `{{"user_query": "<the user's text or a short summary>"}}` and context noting it is not a comp question. Do not invent another plan.

**Mixed questions:** if part is comp and part is not, answer the comp part with data tools; you may add `decline_unrelated_query` for the out-of-domain part, or one decline if the comp part is empty—prefer real tools when a clear comp ask exists.

Rules (in-scope work):
- If the user names a person, start with get_employee unless you already have employee_id. Then use that employee's id in compare_to_market, check_band_position, or follow-ups.
- For any individual employee comp (market competitiveness, pay vs. peers, "are they paid fairly"), you must include check_band_position (after get_employee). Internal band (min/mid/max) and market (percentiles) together describe full comp; the run also auto-adds a band check if the plan omits it.
- For department/team questions, use analyze_team with the right analysis_type, or list_employees to narrow, then market/band tools.
- If you need location-specific market data, you must have role, level, and location: use get_market_benchmarks or list_employees + compare_to_market per person.
- Never invent data; tools read only from the fixture datasets.
- For each task, set params_json to a minified JSON object of keyword args (e.g. {{"name":"Jamie Chen"}} for get_employee). Drafts may be rough: a follow-up pass will rewrite them to match each tool's exact parameters.
- After a get_employee task, you may use {{}} for compare_to_market, check_band_position, get_market_benchmarks, or get_comp_band; the plan-time param normalizer plus the executor param-resolver can fill fields from the user question and from prior tool JSON, with rule-based fallback for ids.
"""

    try:
        plan: SupervisorPlan = structured.invoke(
            [
                SystemMessage(content=system),
                HumanMessage(content=state.get("original_query", "")),
            ],
            config=config,
        )
    except Exception as e:
        # Fallback: single discovery step
        plan = SupervisorPlan(
            main_objective="Answer the comp question using fixture data (planner error)",
            context=f"Supervisor model error: {e!r}",
            tasks=[
                PlanTaskOut(
                    task_id="t0",
                    tool_name="list_employees",
                    params_json="{}",
                    context="List all employees; narrow follow-up in reducer",
                )
            ],
        )

    uq = state.get("original_query", "") or ""
    plan_steps: list[dict] = []
    for t in plan.tasks:
        try:
            pr = json.loads(t.params_json) if t.params_json.strip() else {}
            if not isinstance(pr, dict):
                pr = {}
        except Exception:
            pr = {}
        plan_steps.append(
            {
                "task_id": t.task_id,
                "tool_name": t.tool_name,
                "params": pr,
                "context": t.context,
            }
        )
    try:
        normalized = normalize_plan_drafts(
            plan_steps=plan_steps,
            user_query=uq,
            main_objective=plan.main_objective,
            supervisor_context=plan.context,
            model=state.get("model"),
            config=config,
        )
    except Exception:
        normalized = [dict(s.get("params") or {}) for s in plan_steps]

    task_states: list[TaskState] = []
    for i, t in enumerate(plan.tasks):
        pr: dict
        if i < len(normalized) and isinstance(normalized[i], dict):
            pr = dict(normalized[i])
        else:
            try:
                pr = json.loads(t.params_json) if t.params_json.strip() else {}
            except Exception:
                pr = {}
            if not isinstance(pr, dict):
                pr = {}
        task_states.append(
            {
                "task_id": t.task_id,
                "plan_id": plan_id,
                "tool_name": t.tool_name,
                "params": pr,
                "context": t.context,
                "status": "pending",
                "retries": 0,
                "max_retries": 3,
                "result": None,
                "error": None,
            }
        )
    if not task_states and plan.tasks:
        # all tasks had unknown tool names — keep one get_employee to surface error
        task_states = [
            {
                "task_id": "t_fallback",
                "plan_id": plan_id,
                "tool_name": "get_employee",
                "params": {"name": "INVALID_PLAN"},
                "context": "Planner produced unknown tools; use list_employees as fallback in later revision",
                "status": "pending",
                "retries": 0,
                "max_retries": 3,
                "result": None,
                "error": None,
            }
        ]
    if not task_states:
        task_states = [
            {
                "task_id": "t0",
                "plan_id": plan_id,
                "tool_name": "list_employees",
                "params": {},
                "context": "Empty plan: list all employees to ground the run",
                "status": "pending",
                "retries": 0,
                "max_retries": 3,
                "result": None,
                "error": None,
            }
        ]

    # Person-level comp is incomplete without internal band; ensure one band check per plan.
    tool_names = {t["tool_name"] for t in task_states}
    if (
        ("get_employee" in tool_names or "compare_to_market" in tool_names)
        and "check_band_position" not in tool_names
    ):
        n = len(task_states) + 1
        task_states.append(
            {
                "task_id": f"t_band_{n}",
                "plan_id": plan_id,
                "tool_name": "check_band_position",
                "params": {},
                "context": "Internal comp band (min/mid/max) for this employee; required with market for full comp stats.",
                "status": "pending",
                "retries": 0,
                "max_retries": 3,
                "result": None,
                "error": None,
            }
        )

    return {
        "main_objective": plan.main_objective,
        "context": plan.context,
        "tasks": task_states,
        "current_task_index": 0,
        "model": state.get("model", DEFAULT_MODEL),
    }
