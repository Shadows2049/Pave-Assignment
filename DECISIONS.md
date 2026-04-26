# Design Decisions

_This document is as important as your code. We'll discuss it in the live session._

## Run artifacts

All outputs for a run live in **one directory** per run: `output/runs/<run_id>/` (or `PAIGE_OUTPUT_DIR`). The supervisor **plan** is written first as **`plan.json`** and **`plan.md`**, the plan is **printed to the terminal**, and the run pauses for **`Execute this plan? [y/N]:`** (skipped with `python main.py -y` / `auto_approve=True`, or when stdin is not a TTY so jobs do not block). If the user declines, `run_status.json` is set to `cancelled` and execution is skipped. If approved, **`run_status.json`** moves through `executing` → `completed`, and the usual **`summary.md`**, **`trace.json`**, and **`trace.log`** are added. The repo gitignores `output/`. OpenAI `token_usage` is collected via a LangChain callback on graph config; pure-Python tool calls and HITL do not use tokens.

## Tool Design

Seven tools wrap the three fixture modules (`employees.py`, `market_data.py`, `comp_bands.py`) and return a consistent envelope: `source` (which dataset the row came from), `data`, `error`, and optional `metadata`. This keeps the executor and reducer honest about provenance and makes missing data explicit (e.g. `error` on empty market match).

- **Employee tools:** `get_employee` (resolve a name to a record; errors on no match or multiple matches) and `list_employees` (filter by department, role, level, location).
- **Market / bands:** `get_market_benchmarks` and `get_comp_band` for raw percentiles and internal min/mid/max.
- **Analysis:** `compare_to_market`, `check_band_position`, and `analyze_team` (attrition_risk, pay_equity, market_gap) to answer multi-person questions without requiring the model to re-implement comp math in prose.

All tools are wrapped with a `@with_retry` decorator (up to three internal attempts) for transient `Exception`s; business failures (e.g. not found) return `{error: ...}` and are handled in the executor with repair / HITL.

## Agent Architecture

A **LangGraph** workflow: **supervisor** → **executor** (loop) → **reducer**; **HITL** is an extra edge from the executor when a task cannot be repaired.

1. **Supervisor** (gpt-4.1-mini, `with_structured_output`, `method="function_calling"`): turns the user question into a `SupervisorPlan` with `main_objective`, `context`, and an ordered `tasks` list. Each task names one tool; parameters are a JSON string (`params_json`) to satisfy OpenAI strict structured output (no free-form `dict` in the schema). On planner failure, a fallback `list_employees` task runs so the run still returns grounded data.
2. **Executor:** For each task, call `TOOL_REGISTRY[tool](**params)`. If the result has an `error`, increment retries (max 3) and ask a small **repair** LLM pass for new JSON parameters. If still failing, set route to `hitl` and the **HITL** node prompts on the command line for a JSON object of param overrides, then the executor re-runs the task.
3. **Reducer:** Aggregates all tool `result` blobs (with `source` / dataset) and produces the user-facing answer: citations, uncertainty (missing benchmarks, small `sample_size`, national bands vs. location market), and caveats. No new tools in this node.

**Alternatives considered:** A single ReAct loop without an explicit plan is simpler, but a supervisor plan makes multi-step questions debuggable and matches the “assign tools with only the context needed” brief. A dedicated sub-graph per task type was rejected for the MVP time box.

## Evaluation Approach

- **Correctness with respect to data:** The tools are deterministic; manual runs cover representative queries (e.g. Jamie’s competitiveness, engineering attrition ranking). A follow-up would add `pytest` cases that call tools without the LLM and assert percentiles, band position, and analysis rankings against known gold values in the fixture.
- **Process checks:** The structured plan should list `get_employee` before `compare_to_market` when a person is named. Spot-check `tasks[].tool_name` in `--json` output.
- **What “good” means for a comp answer:** Cites dataset, calls out when market is missing, contrasts band (national) vs. market (location), and states uncertainty. The reducer is prompted to do exactly that.

## Chaining get_employee to downstream tools (params)

The supervisor can leave `params_json` partial or empty for follow-on tools. For **every** tool call, the **executor** first runs [`param_resolver.py`](src/agent/param_resolver.py): a small LLM call that receives the **tool name**, **introspected keyword schema** (from `inspect` on the registered function), **draft params** from the plan, **full JSON** of all **prior completed step results** (in order), plus the user and supervisor text. It outputs a single JSON object of kwargs, then we **filter** to allowed parameter names so extra keys do not break tools. This is **one** mechanism for any new tool in `TOOL_REGISTRY` without N×M hand mappings. After that, [`hydration.py`](src/agent/hydration.py) runs as a **safety net** only: if `employee_id` is still missing or not an `emp-…` id, it overwrites from the last resolved employee record. Repair-on-error and HITL still apply after a failed call.

## Ambiguity & Data Quality

- **Missing market rows:** Surfaces as `error` in tool output; reducer is instructed to mention gaps (e.g. no Remote market for some platform roles).
- **Contradictory signals (market vs. band, performance vs. pay):** Brought into the `blocks` sent to the reducer; the model is asked not to pick one number silently and to flag tension.
- **HITL:** Only when tool calls fail after repair attempts—useful for typos, ambiguous names, or parameters the planner got wrong. Non-interactive environments would need a flag to skip (not implemented in the MVP).

## What I'd Do With More Time

- **Eval harness:** gold JSON expectations per tool and full-path integration tests with mocked LLM for supervisor/reducer.
- **Stronger `get_employee`:** fuzzy match scoring + disambiguation question instead of binary error.
- **Streaming and structured final output** (sections + table) for demo polish.
- **HITL over stdin from env/CI** and `interrupt_before` in LangGraph for production-style review.

## AI assistance

Used for code scaffolding, LangGraph wiring, and drafting this document; all runs were spot-checked against the fixture data and the OpenAI error path for `params_json` (structured outputs).
