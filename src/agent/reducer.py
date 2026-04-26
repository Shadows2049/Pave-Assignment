# src/agent/reducer.py
from __future__ import annotations

import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.agent.state import AgentState
from src.agent.supervisor import DEFAULT_MODEL


def reducer_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    """Summarize tool results into a final analyst-style answer (no new tool calls)."""
    llm = ChatOpenAI(model=state.get("model", DEFAULT_MODEL), temperature=0.2)
    # Collect structured provenance for the model
    blocks = []
    for t in state.get("tasks") or []:
        res = t.get("result")
        blocks.append(
            {
                "task_id": t.get("task_id"),
                "tool_name": t.get("tool_name"),
                "context": t.get("context"),
                "source_dataset": (res or {}).get("source") if isinstance(res, dict) else None,
                "data": (res or {}).get("data") if isinstance(res, dict) else res,
                "error": t.get("error") if t.get("status") != "complete" else (res or {}).get("error"),
            }
        )
    tools_used = [b.get("tool_name") for b in blocks if b.get("tool_name")]
    sources = sorted({b.get("source_dataset") for b in blocks if b.get("source_dataset")})
    system = f"""You are Paige, a compensation analyst assistant. Summarize the tool outputs to answer the user.

Required structure in your response (use these exact Markdown headings after your opening summary if any):
## Answer
(Your main narrative — cite specific numbers and roles.)

## Tools used
(Bullet list: each `tool_name` from the run, in a short phrase, e.g. `get_employee` — resolved person record.)

## Data references
(Bullet list: each `source` / dataset you relied on, e.g. `employees`, `market_data`, `comp_bands`, and file hint `*.py` when present in blocks.)

Run metadata:
- run_id: {state.get("run_id", "")!s}
- tools in this run: {tools_used!r}
- source tags seen: {sources!r}

Rules for the Answer section:
- Cite the dataset (source) when stating numbers, e.g. "employees" fixture, "market_data" benchmark, "comp_bands" policy range.
- If market sample_size is small or a benchmark row is missing, call that out explicitly.
- comp_bands are NATIONAL (no location). market_data IS location-specific. Whenever a band result is present, you MUST note this distinction — e.g. "the internal band is a national range and does not adjust for the employee's location; market data for that location would give a more precise external comparison." If market data is missing for the employee's location, explicitly state that the band-only view is national and may not reflect local pay norms.
- If both band and market are present, contrast them and flag any tension (e.g. in-band nationally but below market median locally).
- Be concise, use bullets where helpful, and flag uncertainty. Do not invent data outside the given JSON.
""".strip()
    human = f"""User question: {state.get("original_query", "")!r}

Main objective: {state.get("main_objective", "")!r}
Prior context: {state.get("context", "")!r}

Tool result blocks (JSON), including tool_name and source_dataset per task:
{json.dumps(blocks, indent=2)[:20000]}

Write the final answer for the user following the required structure and headings.
""".strip()
    out = llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=human)], config=config
    )
    text = (out.content or "").strip()
    return {"final_answer": text}
