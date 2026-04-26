# Design Decisions

_This document is as important as your code. We'll discuss it in the live session._

## Run artifacts

All outputs for a run live in **one directory** per run: `output/runs/<run_id>/` (or `PAIGE_OUTPUT_DIR`). The supervisor **plan** is written first as **`plan.json`** and **`plan.md`**, the plan is **printed to the terminal**, then **execution always continues** to the executor and reducer with no confirmation prompt and no blocking `input()` calls. **`run_status.json`** moves through `executing` → `completed`, and **`summary.md`**, **`trace.json`**, and **`trace.log`** are added. The repo gitignores `output/`. OpenAI `token_usage` is collected via a LangChain callback on graph config.

## Tool Design

Eight tools (across five source files) wrap the three fixture modules (`employees.py`, `market_data.py`, `comp_bands.py`) plus a policy layer, and return a consistent envelope: `source` (which dataset the row came from), `data`, `error`, and optional `metadata`. This keeps the executor and reducer honest about provenance and makes missing data explicit (e.g. `error` on empty market match).

| File | Tools | Dataset |
|---|---|---|
| `src/tools/employee_tools.py` | `get_employee`, `list_employees` | `employees.py` |
| `src/tools/market_tools.py` | `get_market_benchmarks` | `market_data.py` |
| `src/tools/band_tools.py` | `get_comp_band` | `comp_bands.py` |
| `src/tools/analysis_tools.py` | `compare_to_market`, `check_band_position`, `analyze_team` | `employees` + `market_data` + `comp_bands` |
| `src/tools/meta_tools.py` | `decline_unrelated_query` | none (policy only) |

Supporting modules:
- **`src/tools/base.py`** — `@with_retry(max_attempts=3)` decorator applied to every tool, plus the `ok` / `err` helpers that produce the standard `{source, data, error, metadata}` envelope.
- **`src/tools/scope.py`** — `is_universal_filter()`, a shared predicate used by `list_employees`, `get_market_benchmarks`, `get_comp_band`, and `analyze_team` to treat tokens like `"all"`, `"company"`, `"*"`, or `None` as "no filter on this field" rather than a literal match. This lets the planner write `department: "all"` and receive company-wide results.
- **`src/tools/__init__.py`** — `TOOL_REGISTRY` (name → callable) and `TOOL_LIST_DESCRIPTION` (the natural-language tool menu injected into the supervisor and param-resolver prompts).

**Per-tool details:**
- **`get_employee(name)`** — case-insensitive substring match; errors if zero or multiple results.
- **`list_employees(department?, role?, level?, location?)`** — all filters optional; universal tokens (`"all"`, etc.) skip that filter.
- **`get_market_benchmarks(role, level, location, component?)`** — any arg can be a universal token for a full-matrix query.
- **`get_comp_band(role, level, component?)`** — national bands only; never accepts `location`.
- **`compare_to_market(employee_id, component="total_comp")`** — looks up the employee and finds the matching `market_data` row for their role/level/location; returns bracket, verdict, and percentiles.
- **`check_band_position(employee_id, component="total_comp")`** — looks up the employee and finds their `comp_bands` row; returns position (below_min / in_band / above_max) and delta from midpoint.
- **`analyze_team(analysis_type, department?)`** — three modes: `attrition_risk` (risk score by market ratio + performance), `pay_equity` (pairwise gender **and** ethnicity gaps within (role, level, location) cohorts), `market_gap` (avg gap vs p50; company-wide run adds `by_department` ranking). Department defaults to all employees when omitted or universal.
- **`decline_unrelated_query(user_query?)`** — returns a fixed `agent_policy` message; reads no fixture data.

## Agent Architecture

A **LangGraph** workflow: **supervisor** → **executor** (loop) → **reducer** (no human-in-the-loop; no runtime input).

1. **Supervisor** (gpt-4.1-mini, `with_structured_output`, `method="function_calling"`): turns the user question into a `SupervisorPlan` with `main_objective`, `context`, and an ordered `tasks` list (1–8 steps). Each task names one tool; parameters are a JSON string (`params_json`) to satisfy OpenAI strict structured output (no free-form `dict` in the schema). The supervisor prompt:
   - Detects **out-of-scope** questions (weather, sports, general knowledge) and routes them to `decline_unrelated_query` instead of calling comp tools.
   - Requires `check_band_position` for any individual-employee comp question; if the plan omits it, the supervisor node **appends** it automatically after the plan is returned.
   - On planner failure, falls back to a single `list_employees` task so the run still returns grounded data.

2. **Plan-time param normalizer** (`param_resolver.normalize_plan_drafts`): After the structured plan is generated, a **second LLM call** (structured `rows`: `task_id` + `params_json`) rewrites every step's draft kwargs into **valid tool parameters**, using introspected signatures for each distinct tool in the plan. It aligns natural-language values (e.g. "all departments" → `department: "all"`), drops unknown keys via `_filter_to_tool_params`, and falls back to original drafts on any exception. This runs **before** the executor, so parameters shown in `plan.md` already match each tool's signature.

3. **Executor:** For each task in order, the executor:
   - Calls `resolve_tool_params` (per-step LLM pass with prior completed-step results) to fill missing fields from context.
   - Runs `hydration.py` as a **safety net**: if `employee_id` is still missing or malformed after resolution, overwrite from the last resolved employee record.
   - Invokes `TOOL_REGISTRY[tool](**params)`.
   - On `error` in the result: increments retries (max 3), calls `_repair_params` (LLM suggests new kwargs), and retries the same step.
   - After max retries: marks the task **`failed`**, stores the last error envelope in `result`, **advances** to the next task, and continues. The run does **not** abort; the reducer handles partial results.

4. **Reducer:** Aggregates all tool `result` blobs (including failed ones, which carry an `error` field) and produces the user-facing answer: citations, uncertainty (missing benchmarks, small `sample_size`, national bands vs. location market), and caveats. No new tool calls.

**Alternatives considered:** A single ReAct loop without an explicit plan is simpler, but a supervisor plan makes multi-step questions debuggable and matches the "assign tools with only the context needed" brief. A dedicated sub-graph per task type was rejected for the MVP time box.

## Param Resolution Pipeline (chain of responsibility)

Every tool invocation goes through three layers in this order:

| Layer | Where | Purpose |
|---|---|---|
| **Plan-time normalizer** | `normalize_plan_drafts` (supervisor node, before executor) | Batch-normalizes all plan steps to valid kwargs using tool signatures and user intent. Shown in `plan.md`. |
| **Per-step resolver** | `resolve_tool_params` (executor, before each call) | Fills fields from prior completed step results (e.g. `employee_id` from a prior `get_employee`). |
| **Hydration safety net** | `hydration.py` (executor, after resolver) | Rule-based override: if `employee_id` is still missing or invalid, inject it from the last employee record in the task list. |

## Out-of-scope detection

The supervisor system prompt explicitly instructs the model to use **`decline_unrelated_query`** when the user's question cannot be answered from the comp fixtures. Examples: weather, sports scores, coding help, general knowledge. For mixed questions (part comp, part not), the planner answers the comp part with data tools and may append a single `decline_unrelated_query` step for the off-topic part. The tool returns a policy message citing Paige's scope; no fixture data is read.

## Always-include band check for individual comp

For any plan containing `get_employee` or `compare_to_market` (individual employee context), the supervisor node appends `check_band_position` if it is missing. Internal band (min/mid/max from `comp_bands.py`) and market (percentiles from `market_data.py`) together give the full picture; neither alone is sufficient. This rule fires both in the supervisor prompt and as a deterministic post-processing step on `task_states`.

## Chaining: params from prior tool outputs

The supervisor may emit partial or empty `params_json` for follow-on tools. The plan-time normalizer and per-step resolver both fill missing fields from user context and prior results. The hydration layer is a final safety net for `employee_id`. For any new tool added to `TOOL_REGISTRY`, `inspect`-based schema introspection provides the parameter names automatically — no N×M hand mapping.

## Graceful failure & data quality

- **Tool failure after retries:** task marked `failed`; run continues; reducer describes partial results and what failed. No crash, no blocking prompt.
- **Missing market rows:** surfaces as `error` in tool output; reducer is instructed to mention gaps (e.g. no Remote market for some platform roles; no London benchmark in `market_data`).
- **Contradictory user input vs. fixture:** planner resolves name via `get_employee` and reports what the data says; does not adopt wrong user "facts" (tested with contradictory attributes for Jamie Chen).
- **Unknown/invalid scope values:** `is_universal_filter` normalises `"all"` / `"company"` / `"*"` to no-filter at the tool level, preventing spurious "no employees" errors when the planner writes a broad scope.
- **Contradictory signals (market vs. band, performance vs. pay):** both are passed to the reducer; the model is prompted to surface the tension rather than silently pick one number.

## Evaluation Approach

- **Correctness with respect to data:** The tools are deterministic. Manual runs cover all six README example queries (q1–q6), a contradictory compound query, a missing-market query (London benchmark), and an out-of-scope query (weather). A follow-up would add `pytest` cases calling tools without the LLM and asserting percentiles, band positions, and analysis rankings against known gold values.
- **Process checks:** The structured plan should list `get_employee` before `compare_to_market` when a person is named; `decline_unrelated_query` when the topic is off-domain; `check_band_position` always alongside market for individuals.
- **What "good" means for a comp answer:** Cites dataset, calls out when market data is missing, contrasts national band vs. location-specific market, states uncertainty, and for off-topic queries declines with a clear scoped-out message rather than hallucinating.

## What I'd Do With More Time

### HITL for runtime data compensation
Re-introduce HITL, but scoped only to **data gaps** rather than parameter typos. When a tool fails after repair retries, instead of silently marking it `failed` and continuing, surface the specific missing field to the user (e.g. *"No market benchmark exists for Platform Engineer L5 in Austin — please supply a P50 override or choose a different location"*). The user's response is injected into `task["params"]` and the step retries. This makes the system resilient to fixture gaps that the LLM cannot guess away, and keeps HITL out of the hot path for happy-path runs. Implementation: LangGraph `interrupt_before` on a dedicated `hitl_data_gap` node, activated only when `status == "failed"` and `error` matches a known "no data" pattern.

### Plan regeneration on failure + user intent change
After HITL input (or on user-initiated intent change mid-run), re-invoke the **supervisor** with a new context block containing: the original query, the completed steps so far, the failed step's error, and the user's correction or new intent. The supervisor produces a **revised plan** that starts from the next pending step — skipping already-completed tasks. This closes the loop on questions like *"that role doesn't exist; use Data Scientist instead"* and turns single-shot plan-then-execute into a **conversational** comp workflow. Key design constraint: completed `TaskState` results must be preserved across plan regenerations so the reducer always has the full picture.

### ReAct architecture comparison
Run the same benchmark queries under a **ReAct** (Reason + Act) loop — model decides each next tool call based on the accumulating observation chain — against the current **plan-then-execute** architecture, measuring: (a) final-answer correctness vs. fixture ground truth, (b) total tokens used, (c) failure rate on multi-step questions, and (d) latency. Hypothesis: ReAct is more adaptive for ambiguous or iterative questions but noisier and higher-cost for deterministic comp math; plan-execute is more auditable and cheaper for structured queries. The evaluation would inform which mode to use by default and whether a hybrid (plan for well-specified queries, ReAct for exploratory ones) is worth the added complexity.

### Migrate tools to Anthropic tool-use / MCP architecture
Replace the current `TOOL_REGISTRY` + `inspect`-based schema introspection with **Anthropic's tool-use format** (JSON Schema `input_schema` per tool), or expose tools as an **MCP server**. Benefits: (a) tool discovery is schema-driven — the model receives only the signatures relevant to the current query rather than the full `TOOL_LIST_DESCRIPTION` string, saving context window; (b) tool definitions live alongside their implementations (`@tool` decorator or MCP `@server.tool()`) so they stay in sync without maintaining a separate `__init__.py` registry; (c) extensibility — adding a new tool means one decorated function, not edits to registry + description + param-resolver prompt; (d) the MCP path enables external clients (Claude Desktop, other agents) to discover and call the same tools without code changes.

## AI assistance

Cursor used for code scaffolding, LangGraph wiring, and drafting this document; all runs were spot-checked against the fixture data and the OpenAI error path for `params_json` (structured outputs).

Sonnet 4.6 for planning; Composer 2 for coding and debugging.
