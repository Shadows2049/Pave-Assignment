# src/agent/state.py
from __future__ import annotations

from typing import Annotated, Any, Literal, NotRequired, TypedDict

from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class TaskState(TypedDict, total=False):
    """A single plan step, mutable during execution."""

    task_id: str
    plan_id: str
    tool_name: str
    params: dict[str, Any]
    context: str
    status: Literal["pending", "running", "complete", "failed"]
    retries: int
    max_retries: int
    result: Any
    error: str | None


class AgentState(TypedDict, total=False):
    run_id: str
    model: str
    original_query: str
    main_objective: str
    context: str
    tool_list: list[str]
    tasks: list[TaskState]
    current_task_index: int
    messages: Annotated[list[BaseMessage], add_messages]
    final_answer: str
    # Routing / internal flags
    executor_route: NotRequired[Literal["continue", "done"]]
    last_tool_error: NotRequired[str | None]
