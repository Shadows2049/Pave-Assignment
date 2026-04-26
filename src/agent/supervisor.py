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
    system = f"""You are a compensation analysis planner. The user will ask a question about employees, market pay, or internal bands.
Break the work into 1-8 tool calls, in a sensible order.

{TOOL_LIST_DESCRIPTION}

Valid tool_name values (exactly):
{tools_allowed}

Rules:
- If the user names a person, start with get_employee unless you already have employee_id. Then use that employee's id in compare_to_market, check_band_position, or follow-ups.
- For department/team questions, use analyze_team with the right analysis_type, or list_employees to narrow, then market/band tools.
- If you need location-specific market data, you must have role, level, and location: use get_market_benchmarks or list_employees + compare_to_market per person.
- Never invent data; tools read only from the fixture datasets.
- For each task, set params_json to a minified JSON object of keyword args (e.g. {{"name":"Jamie Chen"}} for get_employee).
- After a get_employee task, you may use {{}} for compare_to_market, check_band_position, get_market_benchmarks, or get_comp_band; a param-resolver pass fills kwargs from prior tool JSON before each call, with rule-based fallback for ids.
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

    task_states: list[TaskState] = []
    for t in plan.tasks:
        try:
            pr = json.loads(t.params_json) if t.params_json.strip() else {}
            if not isinstance(pr, dict):
                pr = {}
        except Exception:
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

    return {
        "main_objective": plan.main_objective,
        "context": plan.context,
        "tasks": task_states,
        "current_task_index": 0,
        "model": state.get("model", DEFAULT_MODEL),
    }
