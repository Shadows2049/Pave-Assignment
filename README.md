# Paige — Compensation Analyst Agent

Paige is an AI-powered compensation analyst agent built in Python using LangGraph. It answers natural-language compensation questions by reasoning over structured employee, market, and internal band data.

---

## Quick start

### 1. Prerequisites

- Python **3.11+**
- An **OpenAI API key** (the agent uses `gpt-4.1-mini` by default)

### 2. Clone and create a virtual environment

```bash
git clone <repo-url>
cd Pave-Assignment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure your API key

```bash
cp .env.example .env
```

Open `.env` and fill in your key:

```
OPENAI_API_KEY=sk-...
```

---

## Running the agent

```bash
python main.py "Your compensation question here"
```

The agent will:
1. Print a **supervisor plan** (the ordered list of tool calls it intends to make)
2. Execute every step automatically, retrying failed steps with an LLM repair pass
3. Print the final **analyst answer** to stdout
4. Save all run artifacts to `output/runs/<run_id>/`

### Example queries

```bash
# Individual employee — market + band check
python main.py "Is Jamie Chen's total comp competitive?"

# Team attrition risk
python main.py "Who on the engineering team is most at risk of attrition due to comp?"

# Cross-location market comparison
python main.py "Compare our L5 engineer pay to market across all locations."

# Promotion scenario
python main.py "We're promoting Priya Sharma to L5. What should her new comp package look like?"

# Department-level gap
python main.py "Which department has the biggest gap between internal comp and market rates?"

# Pay equity
python main.py "Are there any pay equity concerns I should know about on the platform team?"
```

### CLI options

| Flag | Description |
|---|---|
| `--model MODEL` | Override the OpenAI model (default: `gpt-4.1-mini`) |
| `--no-save` | Skip writing output artifacts to disk |
| `--output-root PATH` | Write artifacts to a custom folder instead of `output/runs/` |
| `--json` | Print the full raw state JSON after the run (useful for debugging) |

```bash
# Use a different model
python main.py "Is Aisha Patel underpaid?" --model gpt-4.1

# Debug: print raw JSON state
python main.py "Attrition risk in engineering" --json

# Don't write artifacts (fast, throwaway runs)
python main.py "List all platform engineers" --no-save

# Write artifacts to a custom folder
python main.py "Pay equity on the platform team" --output-root output/my_eval
```

---

## Project structure

```
Pave-Assignment/
├── main.py                      # CLI entry point
├── requirements.txt
├── .env.example
├── DECISIONS.md                 # Architecture and design rationale
│
├── src/
│   ├── agent/
│   │   ├── graph.py             # LangGraph workflow: supervisor → executor → reducer
│   │   ├── supervisor.py        # Plan generation (structured output) + plan-time param normalizer
│   │   ├── executor.py          # Task loop: resolve → hydrate → invoke → repair → fail
│   │   ├── reducer.py           # Synthesize tool results into final analyst answer
│   │   ├── param_resolver.py    # LLM-based param normalizer (plan-time) and per-step resolver
│   │   ├── hydration.py         # Safety net: inject employee_id from prior results
│   │   ├── state.py             # AgentState and TaskState TypedDicts
│   │   └── artifacts.py         # Write plan.json, plan.md, summary.md, trace.json, trace.log
│   │
│   ├── tools/
│   │   ├── __init__.py          # TOOL_REGISTRY + TOOL_LIST_DESCRIPTION
│   │   ├── employee_tools.py    # get_employee, list_employees
│   │   ├── market_tools.py      # get_market_benchmarks
│   │   ├── band_tools.py        # get_comp_band
│   │   ├── analysis_tools.py    # compare_to_market, check_band_position, analyze_team
│   │   ├── meta_tools.py        # decline_unrelated_query (scope guard)
│   │   ├── scope.py             # is_universal_filter ("all", "company", "*" → no filter)
│   │   └── base.py              # @with_retry decorator, ok/err envelope helpers
│   │
│   └── data/
│       ├── employees.py         # ~30 employees (comp, performance, demographics, org)
│       ├── market_data.py       # Market percentiles by role / level / location
│       └── comp_bands.py        # Internal bands (min / mid / max) by role / level
│
└── output/                      # Git-ignored; all run artifacts land here
    └── runs/<run_id>/
        ├── plan.json
        ├── plan.md
        ├── run_status.json
        ├── summary.md           # Human-readable answer + execution trace
        ├── trace.json
        └── trace.log
```

---

## Run artifacts

Every run writes to `output/runs/<run-id>/` (or `--output-root`):

| File | Contents |
|---|---|
| `plan.md` / `plan.json` | Supervisor plan: objective, context, ordered tool steps with params |
| `run_status.json` | `executing` → `completed` (or `failed`) with timestamps |
| `summary.md` | Full answer, tools used, data sources, execution trace with retries |
| `trace.json` | Step-by-step state snapshots for debugging |
| `trace.log` | Human-readable trace log |

---

## Architecture overview

```
User query
    │
    ▼
Supervisor (gpt-4.1-mini)
  ├─ Detects out-of-scope queries → decline_unrelated_query
  ├─ Produces ordered task list (1–8 tools)
  └─ Plan-time param normalizer: batch-rewrites all task params to match tool signatures
    │
    ▼
Executor loop (per task)
  ├─ Per-step resolver: fill missing fields from prior completed step results
  ├─ Hydration safety net: inject employee_id from last resolved employee
  ├─ Invoke TOOL_REGISTRY[tool](**params)
  ├─ On error: repair LLM pass (max 3 retries)
  └─ On exhausted retries: mark failed, advance, continue
    │
    ▼
Reducer (gpt-4.1-mini)
  └─ Synthesize all results (including failures) into final answer with citations
```

See [`DECISIONS.md`](DECISIONS.md) for full design rationale, tool inventory, param resolution pipeline, graceful failure design, and future roadmap.

---

## Fixture data

| File | Description |
|---|---|
| `src/data/employees.py` | ~30 employees — comp breakdown, performance rating, demographics, org |
| `src/data/market_data.py` | Market percentiles (p25/p50/p75/p90) by role, level, location |
| `src/data/comp_bands.py` | Internal min/mid/max bands by role and level (national, no location) |

