# src/agent/executor.py
from __future__ import annotations

import copy
import inspect
import json
import traceback
from typing import Any, Literal

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from src.agent.hydration import latest_employee_record_from_tasks, merge_params_from_prior_employee
from src.agent.param_resolver import resolve_tool_params
from src.agent.state import AgentState, TaskState
from src.tools import TOOL_REGISTRY

from src.agent.supervisor import DEFAULT_MODEL


def _llm(*, model: str | None = None) -> ChatOpenAI:
    return ChatOpenAI(model=model or DEFAULT_MODEL, temperature=0)


def _is_tool_ok(res: Any) -> bool:
    if not isinstance(res, dict):
        return False
    return res.get("error") is None and (res.get("data") is not None or "source" in res)


def _repair_params(
    tool_name: str,
    params: dict,
    context: str,
    err_msg: str,
    user_query: str,
    task_ctx: str,
    *,
    model: str | None = None,
    config: RunnableConfig | None = None,
) -> dict:
    """Ask the model to return fixed keyword params as JSON for this tool only."""
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        return params
    try:
        sig = inspect.signature(fn)
        param_docs = {p: str(sig.parameters[p].default) for p in sig.parameters if p != "self"}
    except Exception:
        param_docs = {}
    llm = _llm(model=model)
    prompt = f"""The tool `{tool_name}` was called and returned an error: {err_msg!r}.
Original user question: {user_query!r}
Task note: {task_ctx!r}
Current params: {json.dumps(params)}
Tool parameter schema hint: {param_docs}
Context: {context}

Return ONLY a JSON object with the corrected keyword arguments for `{tool_name}`.
Use the same key names. Do not add null keys unless needed.
""".strip()
    out = llm.invoke(
        [SystemMessage(content="You only output valid minified JSON objects."), HumanMessage(content=prompt)],
        config=config,
    )
    text = (out.content or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if "```" in text:
            text = text.rsplit("```", 1)[0]
    try:
        fixed = json.loads(text)
        if isinstance(fixed, dict):
            return fixed
    except Exception:
        pass
    return params


def _invoke_tool(name: str, params: dict) -> dict:
    if name not in TOOL_REGISTRY:
        return {
            "source": "tool_error",
            "data": None,
            "error": f"Unknown tool: {name!r}. Known: {list(TOOL_REGISTRY)}",
        }
    fn = TOOL_REGISTRY[name]
    try:
        return fn(**params)
    except TypeError as e:
        return {"source": "tool_error", "data": None, "error": f"TypeError: {e}"}
    except Exception as e:
        return {
            "source": "tool_error",
            "data": None,
            "error": f"{e.__class__.__name__}: {e}\n{traceback.format_exc()[-400:]}",
        }


def executor_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    tasks = state.get("tasks") or []
    idx = int(state.get("current_task_index", 0))
    if not tasks or idx >= len(tasks):
        return {"executor_route": "done", "current_task_index": len(tasks)}

    t = copy.deepcopy(tasks[idx])
    t.setdefault("retries", 0)
    t.setdefault("max_retries", 3)
    t["status"] = "running"
    t.setdefault("error", None)

    name = t.get("tool_name", "")
    draft = copy.deepcopy(t.get("params") or {})
    uq = state.get("original_query", "")

    resolved = resolve_tool_params(
        tool_name=name,
        draft_params=draft,
        tasks=tasks,  # type: ignore[arg-type]
        current_index=idx,
        user_query=uq,
        task_note=(t.get("context") or ""),
        supervisor_context=state.get("context") or "",
        model=state.get("model"),
        config=config,
    )
    emp = latest_employee_record_from_tasks(tasks, idx)  # type: ignore[arg-type]
    params = merge_params_from_prior_employee(name, resolved, emp or {})
    t["params"] = copy.deepcopy(params)

    res = _invoke_tool(name, params)
    if _is_tool_ok(res):
        t["result"] = res
        t["error"] = None
        t["status"] = "complete"
        tasks = tasks[:]
        tasks[idx] = t
        return {
            "tasks": tasks,
            "current_task_index": idx + 1,
            "last_tool_error": None,
            "executor_route": "continue" if (idx + 1) < len(tasks) else "done",
        }

    err_msg = (res or {}).get("error") or "Unknown tool failure"
    t["error"] = err_msg

    if t["retries"] < t["max_retries"]:
        t["retries"] += 1
        t["status"] = "running"
        new_params = _repair_params(
            name,
            params,
            state.get("context", "") or "",
            err_msg,
            uq,
            t.get("context", "") or "",
            model=state.get("model"),
            config=config,
        )
        t["params"] = new_params
        tasks = tasks[:]
        tasks[idx] = t
        return {"tasks": tasks, "current_task_index": idx, "last_tool_error": err_msg, "executor_route": "continue"}

    # Retries exhausted: record failure and continue (reducer explains partial / errors).
    t["status"] = "failed"
    t["result"] = res
    tasks = tasks[:]
    tasks[idx] = t
    nxt = idx + 1
    return {
        "tasks": tasks,
        "current_task_index": nxt,
        "last_tool_error": err_msg,
        "executor_route": "continue" if nxt < len(tasks) else "done",
    }


def route_after_executor(state: AgentState) -> Literal["executor", "reducer"]:
    r = state.get("executor_route")
    if r == "done":
        return "reducer"
    return "executor"
