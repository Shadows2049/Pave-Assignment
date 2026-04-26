# Paige — Compensation Analyst Agent: Technical Specification

**Version:** 1.0  
**Last updated:** 2026-04-26  
**Stack:** Python 3.11+, LangGraph, LangChain-OpenAI, Pydantic v2, OpenAI `gpt-4.1-mini`

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Repository Layout](#2-repository-layout)
3. [Data Layer — Fixtures & Schemas](#3-data-layer--fixtures--schemas)
4. [Tool Layer](#4-tool-layer)
5. [Agent Layer](#5-agent-layer)
6. [Data Flow & Agentic Wireframe](#6-data-flow--agentic-wireframe)
7. [Param Resolution Pipeline](#7-param-resolution-pipeline)
8. [Decision Logic Reference](#8-decision-logic-reference)
9. [State Schemas](#9-state-schemas)
10. [Tool Envelope Schema](#10-tool-envelope-schema)
11. [Run Artifact Schema](#11-run-artifact-schema)
12. [Error & Failure Handling](#12-error--failure-handling)
13. [Token Accounting](#13-token-accounting)
14. [Configuration & Environment](#14-configuration--environment)

---

## 1. System Overview

Paige is a **plan-then-execute** compensation analyst agent. Given a natural-language question, it:

1. **Plans** — a supervisor LLM produces an ordered list of tool calls.
2. **Normalises** — a batch LLM pass rewrites plan parameters to match exact tool signatures.
3. **Executes** — an executor loop invokes tools one by one, retrying on error.
4. **Synthesises** — a reducer LLM aggregates tool results into a cited analyst answer.

The system is fully **non-interactive** at runtime (no `input()` calls, no blocking). All LLM calls use structured output (`function_calling` method). Execution never aborts on tool failure; failed steps are collected and described in the final answer.

---

## 2. Repository Layout

```
Pave-Assignment/
│
├── main.py                       CLI entry point
├── requirements.txt              Python dependencies
├── .env.example                  API key template
├── .gitignore
├── README.md                     Setup and usage guide
├── DECISIONS.md                  Architecture and design rationale
│
├── docs/
│   └── TECH_SPEC.md              ← this file
│
├── src/
│   ├── data/                     Fixture datasets (static Python modules)
│   │   ├── employees.py          ~30 employees with comp, performance, demographics
│   │   ├── market_data.py        Market benchmarks (percentiles) by role/level/location
│   │   └── comp_bands.py         Internal comp bands (min/mid/max) by role/level
│   │
│   ├── tools/                    Tool layer — pure functions, no LLM calls
│   │   ├── __init__.py           TOOL_REGISTRY + TOOL_LIST_DESCRIPTION
│   │   ├── base.py               @with_retry decorator, ok/err envelope helpers
│   │   ├── scope.py              is_universal_filter() ("all", "company", "*" → no filter)
│   │   ├── employee_tools.py     get_employee, list_employees
│   │   ├── market_tools.py       get_market_benchmarks
│   │   ├── band_tools.py         get_comp_band
│   │   ├── analysis_tools.py     compare_to_market, check_band_position, analyze_team
│   │   └── meta_tools.py         decline_unrelated_query
│   │
│   └── agent/                    Agent layer — LangGraph nodes and orchestration
│       ├── state.py              AgentState and TaskState TypedDicts
│       ├── supervisor.py         Plan generation + plan-time param normalisation
│       ├── param_resolver.py     LLM param normalizer (plan-time batch + per-step)
│       ├── hydration.py          Rule-based employee_id safety net
│       ├── executor.py           Task execution loop with retry and repair
│       ├── reducer.py            Result synthesis into final analyst answer
│       ├── graph.py              LangGraph StateGraph wiring + run_query() entry
│       └── artifacts.py          plan.json, summary.md, trace.json, trace.log writers
│
└── output/                       Git-ignored; per-run artifact directories
    └── runs/<run-id>/
        ├── plan.json
        ├── plan.md
        ├── run_status.json
        ├── summary.md
        ├── trace.json
        └── trace.log
```

---

## 3. Data Layer — Fixtures & Schemas

All fixture data is static Python modules in `src/data/`. They are imported directly by tools — no database, no I/O.

### 3.1 `employees.py`

**Purpose:** The people dataset. Source of truth for who exists in the system.

```python
@dataclass
class Comp:
    base: int           # annual base salary
    equity: int         # annualised vest value
    bonus: int          # target bonus
    total_comp: int     # base + equity + bonus

@dataclass
class Performance:
    rating: Literal["exceptional", "exceeds", "meets", "developing", "below"]
    last_review_date: str   # ISO date string
    summary: str

@dataclass
class Demographics:
    gender: Literal["M", "F", "NB"]
    ethnicity: str          # free text: "Asian", "White", "Black", etc.

@dataclass
class Employee:
    id: str             # e.g. "emp-001"
    name: str
    department: str     # "Engineering", "Platform", "Product", "Design", "Sales", …
    role: str           # "Software Engineer", "Platform Engineer", "Product Manager", …
    level: str          # "L3", "L4", "L5", "L6"
    location: str       # "San Francisco", "New York", "Remote - US"
    manager: str
    start_date: str     # ISO date
    comp: Comp
    performance: Performance
    demographics: Demographics
```

**Fixture size:** ~30 employees across 7 departments.

---

### 3.2 `market_data.py`

**Purpose:** External market benchmarks (percentiles) by role, level, and location.

```python
@dataclass
class MarketBenchmark:
    role: str
    level: str
    location: str
    component: Literal["base", "equity", "bonus", "total_comp"]
    p25: int
    p50: int
    p75: int
    p90: int
    sample_size: int    # number of data points; confidence indicator
    updated_at: str     # ISO date, typically 2025-10-01
```

**Coverage:** Software Engineer (L3–L6), Platform Engineer (L4–L5), Product Manager (L4–L5), Product Designer (L3–L4), Account Executive (L3–L5), Customer Success Manager (L3–L4), Data Scientist (L4–L5), Sales Development Rep (L2). Locations: `San Francisco`, `New York`, `Remote - US` (not all combos exist).

**Known gaps:** Platform Engineer L5 New York, Platform Engineer L3 any location, many roles outside the listed set. Missing rows are a normal feature of the dataset.

---

### 3.3 `comp_bands.py`

**Purpose:** Internal compensation bands — policy ranges independent of location.

```python
@dataclass
class CompBand:
    role: str
    level: str
    component: Literal["base", "equity", "bonus", "total_comp"]
    min: int
    mid: int
    max: int
    updated_at: str     # ISO date, typically 2025-07-01 (older than market_data)
```

**Notes:** National only — no `location` dimension. Updated on a different cadence from `market_data` (can be 6+ months behind).

---

## 4. Tool Layer

### 4.1 `base.py` — Shared infrastructure

| Symbol | Kind | Description |
|---|---|---|
| `with_retry(max_attempts=3)` | decorator | Wraps any tool function. On `Exception`, retries up to `max_attempts`. If still failing, returns a structured error dict (not raises). |
| `ok(source, data, *, metadata)` | helper | Returns `{"source": source, "data": data, "error": None, "metadata": ...}` |
| `err(source, message, *, metadata)` | helper | Returns `{"source": source, "data": None, "error": message, "metadata": ...}` |

All tool functions return this four-key envelope. The executor checks `result.get("error") is None` to decide success.

---

### 4.2 `scope.py` — Universal filter helper

```python
is_universal_filter(value: str | None) -> bool
```

Returns `True` when a filter argument should mean **no filter** (all values). Recognises: `None`, empty string, `"all"`, `"any"`, `"company"`, `"organization"`, `"org"`, `"*"`, `"-"`, `"n/a"`, compound forms like `"all departments"`, `"all_locations"`, etc.

Used in: `list_employees`, `get_market_benchmarks`, `get_comp_band`, `analyze_team`.

---

### 4.3 `employee_tools.py`

#### `get_employee(*, name: str) -> dict`

- **Dataset:** `employees`
- **Logic:** Case-insensitive substring match on `Employee.name`. Returns `ok` with a serialised employee dict, or `err` if zero or multiple matches.
- **Error cases:** No match → `"No employee found matching: {name!r}"`; multiple matches → lists them.

#### `list_employees(*, department?, role?, level?, location?) -> dict`

- **Dataset:** `employees`
- **Logic:** Starts with the full list, filters each dimension if the arg is not universal. `role` is substring match (`r.lower() in e.role.lower()`); others are exact (case-insensitive).
- **Universal tokens:** Any universal value for a field → skip that filter. `list_employees(department="all")` returns all 30 employees.

**Serialised employee record** (both tools emit this shape):

```json
{
  "id": "emp-001",
  "name": "Jamie Chen",
  "department": "Engineering",
  "role": "Software Engineer",
  "level": "L4",
  "location": "San Francisco",
  "manager": "Dana Reeves",
  "start_date": "2022-03-15",
  "comp": { "base": 165000, "equity": 40000, "bonus": 16500, "total_comp": 221500 },
  "performance": { "rating": "exceeds", "last_review_date": "2025-09-01", "summary": "…" },
  "demographics": { "gender": "M", "ethnicity": "Asian" }
}
```

---

### 4.4 `market_tools.py`

#### `get_market_benchmarks(*, role, level, location, component?) -> dict`

- **Dataset:** `market_data`
- **Logic:** Filters `market_data` list by `role`, `level`, `location` (all support universal tokens). Optionally filters by `component`. Returns `ok(list[MarketBenchmark dicts])` or `err` if no rows match.
- **Universal location:** `location="all"` → returns all locations for that role/level.

**Serialised benchmark row:**

```json
{
  "role": "Software Engineer",
  "level": "L4",
  "location": "San Francisco",
  "component": "total_comp",
  "p25": 210000, "p50": 250000, "p75": 295000, "p90": 340000,
  "sample_size": 456,
  "updated_at": "2025-10-01"
}
```

---

### 4.5 `band_tools.py`

#### `get_comp_band(*, role, level, component?) -> dict`

- **Dataset:** `comp_bands`
- **Logic:** Filters by `role` and `level` (both support universal tokens). Optionally filters by `component`. Returns `ok(list[CompBand dicts])` or `err` if no rows match.
- **No location:** comp bands are national; this tool never accepts a `location` parameter.

**Serialised band row:**

```json
{
  "role": "Software Engineer",
  "level": "L4",
  "component": "total_comp",
  "min": 195000, "mid": 235000, "max": 285000,
  "updated_at": "2025-07-01"
}
```

---

### 4.6 `analysis_tools.py`

#### `compare_to_market(*, employee_id, component="total_comp") -> dict`

- **Datasets:** `employees` + `market_data`
- **Logic:**
  1. Look up employee by `employee_id`.
  2. Read `comp.<component>` (falls back to `total_comp` for unknown components).
  3. Find matching `MarketBenchmark` for `(role, level, location, component)`.
  4. Compute bracket and verdict:
     - `below_p25_susceptible` if value < p25
     - `below_market_median` if value < p50
     - `competitive` if value ≥ p50
- **Output:** employee snapshot + market percentiles + bracket + verdict.
- **Error:** no market row → `err("market_data", "No {component!r} market data for …")`.

#### `check_band_position(*, employee_id, component="total_comp") -> dict`

- **Datasets:** `employees` + `comp_bands`
- **Logic:**
  1. Look up employee.
  2. Read `comp.<component>`.
  3. Find matching `CompBand` for `(role, level, component)`.
  4. Compute `position`: `below_min` | `in_band` | `above_max` and `delta_from_mid`.
- **Output:** employee snapshot + band range + position + delta.

#### `analyze_team(*, analysis_type, department?) -> dict`

- **Datasets:** `employees` + `market_data` + `comp_bands` (varies by type)
- **Department:** universal token → all employees; specific name → filtered team. Errors if no employees found.
- **Analysis types:**

| `analysis_type` | Logic | Key output fields |
|---|---|---|
| `attrition_risk` | Per employee: compute `vs_market_p50_ratio = total_comp / market_p50`. Score `0.8` if ratio < 0.9 and high performer; `0.4` if < 1.0 and performer; `0.5` if < 0.85. Sort descending by risk. | `ranked: [{employee, total_comp, performance, vs_market_p50_ratio, attrition_risk_score}]` |
| `pay_equity` | Group by `(role, level, location)`. For each group with 2+ people: compare average `total_comp` pairwise by **gender** and by **ethnicity**. Flag if spread > 10%. | `groups, potential_gaps: [{dimension, role, level, location, avg_total_comp, spread_pct}]` |
| `market_gap` | Per employee: `gap_vs_p50 = total_comp - market_p50`. Average across valid rows. If `department="all"`: also aggregate by department, sort by absolute avg gap, expose `highest_abs_gap_department`. | `average_gap_vs_market_p50, per_employee, [by_department, highest_abs_gap_department]` |

---

### 4.7 `meta_tools.py`

#### `decline_unrelated_query(*, user_query="") -> dict`

- **Dataset:** none
- **Logic:** Returns a fixed `agent_policy` message stating Paige's compensation-only scope. The `user_query` arg is echoed in `metadata` for traceability.
- **Used by:** supervisor when it detects an out-of-scope question.

---

### 4.8 `__init__.py` — Registry and description

```python
TOOL_REGISTRY: dict[str, Callable[..., dict]] = {
    "decline_unrelated_query": decline_unrelated_query,
    "get_employee": get_employee,
    "list_employees": list_employees,
    "get_market_benchmarks": get_market_benchmarks,
    "get_comp_band": get_comp_band,
    "compare_to_market": compare_to_market,
    "check_band_position": check_band_position,
    "analyze_team": analyze_team,
}
```

`TOOL_LIST_DESCRIPTION` is a markdown-formatted string (injected into the supervisor system prompt and param-resolver prompts) that describes each tool, its parameters, and the universal filter convention.

---

## 5. Agent Layer

### 5.1 `state.py` — Shared state schemas

See [Section 9](#9-state-schemas) for full field-by-field documentation.

### 5.2 `supervisor.py` — Plan generation

**LLM:** `gpt-4.1-mini`, `temperature=0`, `with_structured_output(SupervisorPlan, method="function_calling")`

**Structured output types:**

```python
class PlanTaskOut(BaseModel):
    task_id: str        # e.g. "t1", "t2"
    tool_name: str      # exact TOOL_REGISTRY key
    params_json: str    # minified JSON string (avoids open dict in strict schema)
    context: str        # one-line rationale

class SupervisorPlan(BaseModel):
    main_objective: str
    context: str        # condensed user intent
    tasks: list[PlanTaskOut]  # min_length=1, max 8
```

**System prompt rules (key excerpts):**
- Out-of-scope query → single `decline_unrelated_query` task.
- Named person → `get_employee` first, then `compare_to_market` / `check_band_position`.
- Individual employee question → must include `check_band_position`.
- Drafts may be rough; a follow-up normalizer pass rewrites params.
- Never invent data outside fixtures.

**Post-plan logic (deterministic, in code):**
1. Parse each `params_json` → `dict` (fallback `{}` on error).
2. Invoke `normalize_plan_drafts(plan_steps, ...)` — batch LLM rewrite.
3. Auto-append `check_band_position` task if plan has `get_employee` or `compare_to_market` but not `check_band_position`.
4. Fallback task list if plan is empty or all tools are unknown.

---

### 5.3 `param_resolver.py` — Param normalisation

Two public functions:

#### `normalize_plan_drafts(plan_steps, user_query, main_objective, supervisor_context, model?, config?) -> list[dict]`

**When:** Called once by the supervisor node, immediately after structured plan generation, before the executor sees any tasks.

**What it does:**
- Collects unique `tool_name` values; introspects their signatures via `inspect`.
- Sends a single LLM call with all plan steps' `task_id + tool_name + draft params + context`, the tool signature docs, and user intent.
- LLM returns `_PlanNormOut(rows=[_PlanNormEntry(task_id, params_json)])`.
- Each row is parsed and run through `_filter_to_tool_params` (drops keys not in the signature).
- Matches rows to steps by `task_id`; falls back to positional index if counts match; falls back to original draft on failure.

**Structured output types:**
```python
class _PlanNormEntry(BaseModel):
    task_id: str
    params_json: str    # minified JSON of valid kwargs

class _PlanNormOut(BaseModel):
    rows: list[_PlanNormEntry]
```

#### `resolve_tool_params(tool_name, draft_params, tasks, current_index, user_query, task_note, supervisor_context, model?, config?) -> dict`

**When:** Called by the executor before each individual tool invocation.

**What it does:**
- Collects all prior **completed** task results into a JSON block.
- Sends a single LLM call with tool signature, draft params, prior results, and user context.
- LLM returns `_ResolvedOut(params_json)`.
- Filtered through `_filter_to_tool_params`.
- On exception: returns `draft_params` unchanged.

**Key use case:** `employee_id` for `compare_to_market` / `check_band_position` is often empty in the plan but present in the prior `get_employee` result; the resolver reads it from the JSON.

---

### 5.4 `hydration.py` — Safety net

Runs **after** `resolve_tool_params`, before the tool call. Pure Python, no LLM.

#### `latest_employee_record_from_tasks(tasks, before_index) -> dict | None`

Walks completed tasks backwards from `before_index`, returns the first employee dict with a valid `id` from `get_employee` or a singleton `list_employees` result.

#### `merge_params_from_prior_employee(tool_name, params, emp) -> dict`

Fills missing fields from the employee record:

| Tool | Fields filled if missing |
|---|---|
| `compare_to_market` | `employee_id` (if not `emp-…`) |
| `check_band_position` | `employee_id` (if not `emp-…`) |
| `get_market_benchmarks` | `role`, `level`, `location` |
| `get_comp_band` | `role`, `level` |

---

### 5.5 `executor.py` — Execution loop

Processes one task per graph invocation (LangGraph re-enters the node until all tasks are done).

**Per-task flow:**

```
1. Copy task (deep copy prevents state mutation)
2. resolve_tool_params()     ← per-step LLM resolver
3. merge_params_from_prior_employee()  ← hydration safety net
4. _invoke_tool(name, params)
   ├─ OK  → status="complete", advance index, route="continue"|"done"
   └─ ERR → check retries
       ├─ retries < max_retries (3):
       │     retries += 1
       │     _repair_params()  ← small LLM with error message
       │     re-queue same index, route="continue"
       └─ retries exhausted:
             status="failed", result=last_error_envelope
             advance index, route="continue"|"done"
```

**`_invoke_tool`:** Calls `TOOL_REGISTRY[name](**params)`. Handles: unknown tool name → structured error dict; `TypeError` → structured error dict; any other exception → structured error dict with traceback tail.

**`_repair_params`:** LLM call with the tool's introspected signature, current params, and error message. Returns a corrected `dict` (filtered to tool params). On failure returns original params.

**`route_after_executor`:** Returns `"reducer"` when `executor_route == "done"`, else `"executor"`.

---

### 5.6 `reducer.py` — Answer synthesis

**LLM:** `gpt-4.1-mini`, `temperature=0.2`

**Input:** Collects all `TaskState` entries → builds `blocks`:

```python
{
  "task_id": ...,
  "tool_name": ...,
  "context": ...,
  "source_dataset": result["source"] if complete else None,
  "data": result["data"],
  "error": task["error"] if not complete else result.get("error")
}
```

**System prompt requirements (enforced by heading structure):**
- `## Answer` — narrative with specific numbers, dataset citations.
- `## Tools used` — bullet per tool with one-line description.
- `## Data references` — bullet per dataset seen.

**Rules injected:**
- Cite source dataset for every number.
- Flag small `sample_size` or missing benchmark rows.
- Note that `comp_bands` are national and potentially older than `market_data`.
- Surface contradictory signals; do not silently pick one.
- For failed tool steps: explain what data is missing.

---

### 5.7 `graph.py` — LangGraph wiring

#### `build_graph()` — Full graph (supervisor-included, for tests)

```
START → supervisor → executor ─┬→ executor (loop)
                                └→ reducer → END
```

#### `build_executor_graph()` — Execution-only graph (used by `run_query`)

```
START → executor ─┬→ executor (loop)
                  └→ reducer → END
```

#### `run_query(query, *, model?, save_artifacts?, output_root?) -> dict`

Main public entry point. Sequence:

1. Build initial `AgentState` with `run_id`, `model`, `original_query`, `tool_list`.
2. Attach `LLMTokenLedger` callback handler to LangChain config.
3. Create run directory under `output/runs/<run_id>/` (if `save_artifacts`).
4. Call `supervisor_node(init, config)` — produces plan + normalised params.
5. Write `plan.json` / `plan.md`.
6. Print plan to stdout (`format_plan_for_display`).
7. Set `run_status = "executing"`.
8. Stream `build_executor_graph()` — executor loop → reducer.
9. On completion: write `summary.md`, `trace.json`, `trace.log`, `run_status = "completed"`.
10. Return `out` dict containing `final_answer`, `tasks`, `artifact_paths`, `token_usage`, timing.

---

### 5.8 `artifacts.py` — Run artifact writers

| Symbol | Description |
|---|---|
| `LLMTokenLedger` | Accumulates `prompt_tokens`, `completion_tokens`, `total_tokens` from LangChain `on_llm_end` callbacks. |
| `make_token_handler(ledger)` | Returns a `BaseCallbackHandler` that feeds into the ledger. |
| `state_to_jsonable(state)` | Converts `AgentState` to a JSON-serialisable dict (normalises `BaseMessage` objects and large tool results). |
| `write_plan_files(run_dir, state, *, approved, md_preamble)` | Writes `plan.json` + `plan.md`. |
| `write_run_status(run_dir, status, **extra)` | Writes `run_status.json`. |
| `write_run_artifacts(...)` | Writes `summary.md`, `trace.json`, `trace.log`. |
| `format_plan_for_display(state)` | Returns the terminal-printed plan block. |
| `default_run_dir(root, run_id)` | Returns `root / run_id` (no timestamp prefix). |

---

## 6. Data Flow & Agentic Wireframe

### 6.1 End-to-end request flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CLI  python main.py "Is Jamie Chen's total comp competitive?"               │
└───────────────────────────┬─────────────────────────────────────────────────┘
                             │ run_query(query, ...)
                             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  graph.py :: run_query                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  1. Build AgentState (run_id, model, original_query, tool_list)     │    │
│  │  2. Attach LLMTokenLedger callback                                  │    │
│  │  3. Create output/runs/<run_id>/ directory                          │    │
│  └────────────────────────┬────────────────────────────────────────────┘    │
│                            │                                                 │
│  ┌─────────────────────────▼──────────────────────────────────────────┐     │
│  │  SUPERVISOR NODE  (supervisor.py)                                   │     │
│  │                                                                     │     │
│  │  a. LLM call → SupervisorPlan (main_objective, context, tasks[])   │     │
│  │  b. Parse params_json → dict for each task                         │     │
│  │  c. normalize_plan_drafts() ← LLM batch param rewrite              │     │
│  │  d. Auto-append check_band_position if missing for individual      │     │
│  │  e. Fallback task if plan empty / all unknown tools                │     │
│  └────────────────────────┬────────────────────────────────────────────┘    │
│                            │                                                 │
│  ┌─────────────────────────▼──────────────────────────────────────────┐     │
│  │  write plan.json / plan.md                                          │     │
│  │  print plan to stdout                                               │     │
│  │  set run_status = "executing"                                       │     │
│  └────────────────────────┬────────────────────────────────────────────┘    │
│                            │ stream executor graph                           │
│  ┌─────────────────────────▼──────────────────────────────────────────┐     │
│  │  EXECUTOR NODE  (executor.py)  ← loops until all tasks done         │     │
│  │                                                                     │     │
│  │  For each task at current_task_index:                               │     │
│  │    1. resolve_tool_params()  ← LLM, uses prior results             │     │
│  │    2. merge_params_from_prior_employee()  ← hydration              │     │
│  │    3. TOOL_REGISTRY[tool_name](**params)                            │     │
│  │       ├─ result.error is None  → status="complete", advance        │     │
│  │       └─ result.error present                                      │     │
│  │             ├─ retries < 3  → _repair_params(), retry same step    │     │
│  │             └─ retries == 3 → status="failed", advance             │     │
│  │                                                                     │     │
│  │  route_after_executor():                                            │     │
│  │    executor_route=="done"  → "reducer"                             │     │
│  │    else                    → "executor"  (re-enter)                │     │
│  └────────────────────────┬────────────────────────────────────────────┘    │
│                            │                                                 │
│  ┌─────────────────────────▼──────────────────────────────────────────┐     │
│  │  REDUCER NODE  (reducer.py)                                         │     │
│  │                                                                     │     │
│  │  Collect blocks from all tasks (complete + failed)                  │     │
│  │  LLM call → final_answer (## Answer / ## Tools used / ## Data refs)│     │
│  └────────────────────────┬────────────────────────────────────────────┘    │
│                            │                                                 │
│  ┌─────────────────────────▼──────────────────────────────────────────┐     │
│  │  write summary.md, trace.json, trace.log                            │     │
│  │  set run_status = "completed"                                       │     │
│  │  return out dict                                                    │     │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 6.2 LangGraph state graph (executor subgraph)

```
      ┌─────────┐
      │  START  │
      └────┬────┘
           │
           ▼
      ┌──────────┐      executor_route == "continue"
      │ executor │ ◄──────────────────────────────────┐
      └────┬─────┘                                    │
           │                                          │
           │ route_after_executor()                   │
           │                                          │
     ┌─────┴─────┐                                    │
     │           │                                    │
  "reducer"   "executor" ──────────────────────────────┘
     │
     ▼
 ┌─────────┐
 │ reducer │
 └────┬────┘
      │
      ▼
   ┌──────┐
   │  END │
   └──────┘
```

---

### 6.3 Param resolution pipeline (per-task detail)

```
Plan step (task_id, tool_name, params, context)
  │
  │  [PLAN-TIME — once per run, before executor]
  ▼
normalize_plan_drafts()
  ├─ Input: all plan steps, user query, main_objective, supervisor context
  ├─ LLM: batch _PlanNormOut(rows=[{task_id, params_json}])
  ├─ Filter: _filter_to_tool_params() per row
  └─ Output: list of param dicts, same order as plan steps
  │
  │  [PER-STEP — inside executor, before each tool call]
  ▼
resolve_tool_params()
  ├─ Input: tool_name, draft_params, all prior completed results, user query
  ├─ LLM: _ResolvedOut(params_json)
  ├─ Filter: _filter_to_tool_params()
  └─ Output: param dict with fields filled from prior results
  │
  ▼
merge_params_from_prior_employee()  [hydration — rule-based, no LLM]
  ├─ latest_employee_record_from_tasks() ← scan completed tasks for emp record
  └─ Fill: employee_id / role / level / location if still missing
  │
  ▼
TOOL_REGISTRY[tool_name](**final_params)
```

---

## 7. Param Resolution Pipeline

### 7.1 Why three layers

| Layer | Trigger | Mechanism | Purpose |
|---|---|---|---|
| Plan-time normaliser | Once, after supervisor LLM | Batch LLM (signatures + all steps) | Aligns natural-language values ("all departments") to valid kwargs before execution begins. Results visible in `plan.md`. |
| Per-step resolver | Before every tool call | Per-call LLM (prior results + current step) | Fills fields that depend on prior tool outputs (e.g. `employee_id` from `get_employee`). Dynamic, not known at plan time. |
| Hydration | After per-step resolver | Rule-based Python | Last-resort: employee_id, role, level, location from the most recent resolved employee. Zero tokens; no LLM. |

### 7.2 `_filter_to_tool_params`

```python
def _filter_to_tool_params(tool_name: str, d: dict) -> dict:
    names = _tool_kw_names(tool_name)  # inspect.signature → set of param names
    if not names:
        return d
    return {k: v for k, v in d.items() if k in names}
```

Prevents `TypeError` from over-eager LLM-generated keys that don't exist in the tool signature.

---

## 8. Decision Logic Reference

### 8.1 Scope detection

```
User query
  │
  ▼ Supervisor system prompt evaluation (LLM)
  ├─ Topic: weather / news / general knowledge / non-HR content
  │   └─ Plan: [decline_unrelated_query(user_query=...)]
  │
  └─ Topic: compensation / employees / market / bands
      └─ Plan: [comp tools ...]
```

### 8.2 Individual employee comp — always-band rule

```
Supervisor produces plan
  │
  ▼ supervisor_node post-processing (deterministic Python)
  ├─ tool_names = {t["tool_name"] for t in task_states}
  ├─ If "get_employee" ∈ tool_names OR "compare_to_market" ∈ tool_names
  │   AND "check_band_position" ∉ tool_names
  └─   → append TaskState(tool_name="check_band_position", params={}, ...)
```

### 8.3 Tool execution — retry / repair / fail

```
invoke tool
  │
  ├─ result.error is None  ──────────────────► status="complete", next task
  │
  └─ result.error present
       │
       ├─ task.retries < task.max_retries (3)
       │     task.retries += 1
       │     _repair_params(tool, params, error_msg)  ← LLM
       │     re-invoke same task
       │
       └─ task.retries == task.max_retries
             status="failed"
             result = last_error_envelope
             advance to next task
             (run continues; reducer handles partial data)
```

### 8.4 Universal filter resolution

```
Tool receives filter argument (e.g. department="all")
  │
  ▼ is_universal_filter(value)
  ├─ True  → skip this filter (all rows pass)
  └─ False → apply exact / substring match
```

### 8.5 `analyze_team` — market_gap company-wide aggregation

```
analyze_team(analysis_type="market_gap", department="all")
  │
  ├─ Compute per-employee gap: e.comp.total_comp - market_p50 (None if no market row)
  ├─ Compute company-wide average_gap_vs_market_p50
  ├─ Group by e.department → by_dept_vals: dict[dept_name, list[float]]
  ├─ Compute avg per department
  ├─ Sort by abs(avg) descending
  └─ Expose: by_department[], highest_abs_gap_department
```

### 8.6 `analyze_team` — pay_equity demographic gaps

```
For each (role, level, location) cohort with ≥2 employees:
  │
  ├─ by_gender = group total_comp by e.demographics.gender
  ├─ by_ethnicity = group total_comp by e.demographics.ethnicity
  │
  └─ _pairwise_demographic_gaps(key, bucket, dimension):
       For each pair (A, B) of demographic groups:
         a_avg = mean(bucket[A])
         b_avg = mean(bucket[B])
         if |a_avg - b_avg| / max(a_avg, b_avg) > 0.10:
           → flag {dimension, role, level, location, avg_total_comp, spread_pct}
```

---

## 9. State Schemas

### 9.1 `TaskState` (`state.py`)

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | Unique within a plan, e.g. `"t1"`, `"t_band_4"` |
| `plan_id` | `str` | 8-char hex, identifies the plan batch this task belongs to |
| `tool_name` | `str` | Exact `TOOL_REGISTRY` key |
| `params` | `dict[str, Any]` | Final resolved kwargs (after normaliser + resolver + hydration) |
| `context` | `str` | One-line rationale from the supervisor |
| `status` | `Literal["pending","running","complete","failed"]` | Lifecycle state |
| `retries` | `int` | Number of repair attempts consumed |
| `max_retries` | `int` | Maximum repairs (default `3`) |
| `result` | `Any` | Tool envelope `{source, data, error, metadata}` after invocation |
| `error` | `str | None` | Last error message (None on success) |

### 9.2 `AgentState` (`state.py`)

| Field | Type | Description |
|---|---|---|
| `run_id` | `str` | UUID4 string, unique per run |
| `model` | `str` | OpenAI model name, e.g. `"gpt-4.1-mini"` |
| `original_query` | `str` | User's raw question |
| `main_objective` | `str` | Supervisor's one-line objective |
| `context` | `str` | Supervisor's condensed intent |
| `tool_list` | `list[str]` | Sorted list of all `TOOL_REGISTRY` keys |
| `tasks` | `list[TaskState]` | All planned task steps, mutated during execution |
| `current_task_index` | `int` | Index into `tasks` of the next task to execute |
| `messages` | `Annotated[list[BaseMessage], add_messages]` | LangGraph message list (append-only) |
| `final_answer` | `str` | Reducer's markdown output |
| `executor_route` | `"continue" | "done"` | LangGraph routing signal |
| `last_tool_error` | `str | None` | Most recent tool error message |

---

## 10. Tool Envelope Schema

Every tool function (except when the `@with_retry` decorator fires after all retries) returns:

```json
{
  "source": "<dataset name or 'agent_policy' or 'tool_error'>",
  "data": <dict | list | null>,
  "error": "<error message string or null>",
  "metadata": {
    "<tool-specific keys>": "..."
  }
}
```

| Field | On success | On business error (`err()`) | On exception (`@with_retry` exhausted) |
|---|---|---|---|
| `source` | dataset name | dataset name | `"tool_error"` |
| `data` | populated | `null` | `null` |
| `error` | `null` | error message string | exception message |
| `metadata` | tool-specific | `{}` or hint | `{retries, tool}` |

The executor checks `result.get("error") is None and (result.get("data") is not None or "source" in result)` for a healthy result.

---

## 11. Run Artifact Schema

### `plan.json`

```json
{
  "run_id": "abc123...",
  "model": "gpt-4.1-mini",
  "original_query": "Is Jamie Chen competitive?",
  "main_objective": "...",
  "context": "...",
  "tasks": [
    { "task_id": "t1", "plan_id": "...", "tool_name": "get_employee", "params": {"name": "Jamie Chen"}, "context": "..." }
  ],
  "approved": true,
  "approved_at": "2026-04-26T19:00:00Z"
}
```

### `run_status.json`

```json
{ "status": "completed", "at": "2026-04-26T19:00:10Z" }
```

Statuses: `"executing"` → `"completed"` (or `"failed"` if an unhandled exception escapes `run_query`).

### `summary.md` — human-readable

```markdown
---
run_id: ...
model: gpt-4.1-mini
plan_approved: True
started_at: ...
finished_at: ...
duration_s: ...
tokens_aggregated: input=... output=... total=...
artifacts: summary.md, trace.json, trace.log, plan.json, plan.md (same folder)
---
# Comp analyst result
## User question
## Objectives (supervisor)
## Model output
## Answer
## Tools used
## Data references
## Execution trace (tool calls, params, retries, sources)
## Datasets referenced (from tool `source` fields)
```

### `trace.json`

Array of step snapshots:

```json
[
  { "step_index": 0, "phase": "supervisor", "timestamp": "...", "elapsed_s": 0.0, "state": { ... } },
  { "step_index": 1, "phase": "executor_graph", "timestamp": "...", "elapsed_s": 2.1, "state": { ... } }
]
```

### `trace.log`

Human-readable text rendering of the trace with task statuses, params, errors, and retries.

---

## 12. Error & Failure Handling

### 12.1 Tool-level errors

| Scenario | Outcome |
|---|---|
| Business error (no matching row, no employee) | `err()` envelope; `error` field populated; tool returns normally |
| Transient Python exception | `@with_retry` retries up to 3×; then returns structured error envelope |
| Unknown tool name | `_invoke_tool` returns `{source: "tool_error", error: "Unknown tool: ..."}` |
| `TypeError` (bad param names/types) | Caught in `_invoke_tool`; returns `{source: "tool_error", error: "TypeError: ..."}` |

### 12.2 Executor-level error handling

```
Tool error → executor repair loop (max 3 retries with _repair_params LLM)
  → on exhaustion: task.status = "failed", result = last error envelope
  → execution continues with next task
  → reducer receives full block including failed tasks
```

### 12.3 No abort path

- The run **never** raises an exception to the caller from within `run_query` due to tool failure.
- The only way `run_query` raises is if the **supervisor LLM call**, **reducer LLM call**, or LangGraph infrastructure itself throws — none of which are compensated for by retry in the current design.

---

## 13. Token Accounting

`LLMTokenLedger` in `artifacts.py` hooks into LangChain's `on_llm_end` callback. It accumulates:

- `total_input_tokens` (prompt tokens)
- `total_output_tokens` (completion tokens)
- `total_tokens`
- Per-call breakdown list

**LLM calls per run (typical):**

| Call | Location | Notes |
|---|---|---|
| Supervisor plan | `supervisor.py` | 1 call |
| Plan-time normaliser | `param_resolver.normalize_plan_drafts` | 1 call |
| Per-step resolver | `param_resolver.resolve_tool_params` | 1 per task |
| Repair | `executor._repair_params` | 0–3 per failed task |
| Reducer synthesis | `reducer.py` | 1 call |

Token totals are written to `summary.md` front-matter and returned in the `run_query` output dict under `token_usage`.

---

## 14. Configuration & Environment

### Environment variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key. Also accepts lowercase `openai_api_key` (mapped in `graph.py`). |
| `PAIGE_OUTPUT_DIR` | No | `output/runs` | Override root directory for run artifacts. |

### CLI flags (`main.py`)

| Flag | Default | Description |
|---|---|---|
| `query` (positional) | — | The natural-language comp question. |
| `--model MODEL` | `gpt-4.1-mini` | OpenAI model ID for all LLM calls. |
| `--no-save` | `False` | Skip writing artifacts to disk. |
| `--output-root PATH` | `None` (uses `PAIGE_OUTPUT_DIR` or default) | Override artifact root for this run. |
| `--json` | `False` | Print full `AgentState` JSON to stdout after run (debug). |

### Dependencies (`requirements.txt`)

| Package | Purpose |
|---|---|
| `langgraph>=0.2.0` | StateGraph orchestration, node wiring, stream |
| `langchain-openai>=0.2.0` | `ChatOpenAI`, `with_structured_output`, callbacks |
| `openai>=1.0.0` | Underlying OpenAI client |
| `pydantic>=2.0.0` | Structured output schemas (`SupervisorPlan`, `_PlanNormOut`, etc.) |
| `python-dotenv>=1.0.0` | `.env` loading |
