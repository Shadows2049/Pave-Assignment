# src/agent/graph.py
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

load_dotenv()
_v = os.getenv("OPENAI_API_KEY") or os.getenv("openai_api_key")
if _v:
    os.environ["OPENAI_API_KEY"] = _v

from src.agent.artifacts import (
    LLMTokenLedger,
    default_run_dir,
    format_plan_for_display,
    make_token_handler,
    state_to_jsonable,
    write_plan_files,
    write_run_artifacts,
    write_run_status,
)
from src.agent.state import AgentState
from src.agent.supervisor import supervisor_node
from src.agent.reducer import reducer_node
from src.agent.executor import executor_node, hitl_node, route_after_executor
from src.tools import TOOL_REGISTRY


def build_graph() -> Any:
    """Full graph: supervisor → … (for tests that need a single app)."""
    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("executor", executor_node)
    g.add_node("hitl", hitl_node)
    g.add_node("reducer", reducer_node)

    g.add_edge(START, "supervisor")
    g.add_edge("supervisor", "executor")
    g.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "executor": "executor",
            "hitl": "hitl",
            "reducer": "reducer",
        },
    )
    g.add_edge("hitl", "executor")
    g.add_edge("reducer", END)
    return g.compile()


def build_executor_graph() -> Any:
    """Execute after a confirmed plan (START at executor)."""
    g = StateGraph(AgentState)
    g.add_node("executor", executor_node)
    g.add_node("hitl", hitl_node)
    g.add_node("reducer", reducer_node)

    g.add_edge(START, "executor")
    g.add_conditional_edges(
        "executor",
        route_after_executor,
        {
            "executor": "executor",
            "hitl": "hitl",
            "reducer": "reducer",
        },
    )
    g.add_edge("hitl", "executor")
    g.add_edge("reducer", END)
    return g.compile()


def _prompt_execute_plan() -> bool:
    """If stdin is not a TTY (piped, CI), do not block — treat as auto-continue."""
    if not sys.stdin.isatty():
        return True
    try:
        ans = input("Execute this plan? [y/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("y", "yes")


def run_query(
    query: str,
    *,
    model: str | None = None,
    save_artifacts: bool = True,
    output_root: Path | None = None,
    auto_approve: bool | None = None,
) -> dict[str, Any]:
    """
    1) Supervisor → plan, saved to output/runs/<run_id>/{plan.json,plan.md}.
    2) Print plan; wait for [y/N] unless auto_approve (or non-tty, auto-continue).
    3) On approval, run executor → reducer. All run artifacts share one run_id folder.
    """
    from langchain_core.messages import HumanMessage

    t0 = time.perf_counter()
    started_at = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    tool_list = sorted(TOOL_REGISTRY)
    m = model or "gpt-4.1-mini"
    init: AgentState = {
        "run_id": run_id,
        "model": m,
        "original_query": query,
        "main_objective": "",
        "context": "",
        "tool_list": tool_list,
        "messages": [HumanMessage(content=query)],
        "current_task_index": 0,
    }

    ledger = LLMTokenLedger()
    token_handler = make_token_handler(ledger)
    config: dict = {"callbacks": [token_handler]}

    run_dir: Path | None = None
    if save_artifacts:
        root = output_root or Path(os.getenv("PAIGE_OUTPUT_DIR", "output/runs"))
        run_dir = default_run_dir(root, run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

    sup_update = supervisor_node(init, config)  # type: ignore[operator]
    state1: dict[str, Any] = {**{k: v for k, v in init.items()}, **dict(sup_update)}  # type: ignore[arg-type]

    plan_paths: dict[str, str] = {}
    if run_dir is not None:
        preamble = f"# Plan — `{run_id}`\n\n**Original query:** {query!r}"
        plan_paths = write_plan_files(
            run_dir, state1, approved=None, md_preamble=preamble
        )

    # Show plan, then confirm
    print(format_plan_for_display(state1), file=sys.stdout)
    if auto_approve is not None:
        approved = bool(auto_approve)
    else:
        approved = _prompt_execute_plan()

    if not approved:
        msg = "Run cancelled: plan not approved (no execution performed)."
        state1["final_answer"] = msg
        state1["plan_approved"] = False
        if run_dir is not None:
            write_plan_files(
                run_dir,
                state1,
                approved=False,
                md_preamble=f"# Plan — `{run_id}`\n\n**Original query:** {query!r}",
            )
            write_run_status(run_dir, "cancelled", reason="user_declined")
            finished_at = datetime.now(timezone.utc).isoformat()
            duration_s = time.perf_counter() - t0
            trace_steps = [
                {
                    "step_index": 0,
                    "phase": "supervisor",
                    "timestamp": started_at,
                    "elapsed_s": 0.0,
                    "state": state_to_jsonable(state1),
                }
            ]
            paths = write_run_artifacts(
                run_dir=run_dir,
                run_id=run_id,
                model=m,
                original_query=query,
                started_at=started_at,
                finished_at=finished_at,
                duration_s=duration_s,
                final_state=dict(state1),
                trace_steps=trace_steps,
                token_ledger=ledger,
                plan_approved=False,
            )
            paths = {**paths, **{k: v for k, v in plan_paths.items() if v}}
            out = dict(state1)
            out["artifact_paths"] = paths
            out["run_dir"] = str(run_dir)
            out["started_at"] = started_at
            out["finished_at"] = finished_at
            out["duration_s"] = round(duration_s, 4)
            out["token_usage"] = ledger.to_dict()
            return out

    if run_dir is not None:
        plan_paths = write_plan_files(
            run_dir,
            state1,
            approved=True,
            md_preamble=f"# Plan — `{run_id}`\n\n**Original query:** {query!r}",
        )
        write_run_status(run_dir, "executing", note="approved")
    state1["plan_approved"] = True

    app_exec = build_executor_graph()
    trace_steps: list[dict[str, Any]] = [
        {
            "step_index": 0,
            "phase": "supervisor",
            "timestamp": started_at,
            "elapsed_s": 0.0,
            "state": state_to_jsonable(state1),
        }
    ]
    last_state: dict[str, Any] = state1
    for i, state in enumerate(
        app_exec.stream(
            state1,  # type: ignore[arg-type]
            config=config,
            stream_mode="values",
        ),
        start=1,
    ):
        elapsed = time.perf_counter() - t0
        ts = datetime.now(timezone.utc).isoformat()
        trace_steps.append(
            {
                "step_index": i,
                "phase": "executor_graph",
                "timestamp": ts,
                "elapsed_s": round(elapsed, 4),
                "state": state_to_jsonable(state),
            }
        )
        if isinstance(state, dict):
            last_state = state

    finished_at = datetime.now(timezone.utc).isoformat()
    duration_s = time.perf_counter() - t0
    out: dict[str, Any] = dict(last_state) if last_state else {}
    if run_dir is not None and save_artifacts:
        paths = write_run_artifacts(
            run_dir=run_dir,
            run_id=run_id,
            model=m,
            original_query=query,
            started_at=started_at,
            finished_at=finished_at,
            duration_s=duration_s,
            final_state=dict(out) if out else {},
            trace_steps=trace_steps,
            token_ledger=ledger,
            plan_approved=True,
        )
        for k, v in plan_paths.items():
            if k not in paths:
                paths[k] = v
        if run_dir is not None:
            write_run_status(run_dir, "completed")
        out["artifact_paths"] = paths
        out["run_dir"] = str(run_dir)

    out["started_at"] = started_at
    out["finished_at"] = finished_at
    out["duration_s"] = round(duration_s, 4)
    out["token_usage"] = ledger.to_dict()
    return out
