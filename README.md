# Technical Exercise: Compensation Analyst Agent

## Context

Pave is building **Paige**, an AI-powered compensation analyst. Paige is an agentic system that sits on top of Pave's proprietary compensation data and workflow engine, helping HR teams and comp leaders make better decisions.

In this exercise, you'll build a small agent that handles one slice of what Paige does: **answering natural language compensation questions by reasoning over structured comp data.**

---

## The Exercise

Build an agent in **Python** that can answer natural language compensation questions like these:

```
"Is Jamie Chen's total comp competitive?"
"Who on the engineering team is most at risk of attrition due to comp?"
"Compare our L5 engineer pay to market across all locations."
"We're promoting Priya Sharma to L5. What should her new comp package look like?"
"Which department has the biggest gap between internal comp and market rates?"
"Are there any pay equity concerns I should know about on the platform team?"
```

These questions range from simple lookups to multi-step analysis to genuinely ambiguous. Your agent should handle a range of them — and handle gracefully the ones it can't fully answer.

---

## What We Provide

**Fixture data** In `src/data/` you'll find three datasets:

- `employees.py` — ~30 employees across engineering, platform, product, design, sales, customer success, and data science. Includes comp breakdowns, performance ratings, demographic data, and org structure.
- `market_data.py` — Market compensation benchmarks (percentiles) by role, level, and location. Sourced from a simulated version of Pave's market dataset.
- `comp_bands.py` — Internal compensation bands (min/mid/max) by role and level.

The data is realistic but synthetic, and it has the kinds of problems you'd find in a real comp system:

- Some role/level/location combinations have no market data
- Comp bands are national but market data is location-specific
- Some employees are outside their band ranges
- Market data sample sizes vary widely (67 to 456)
- Comp bands were last updated 6+ months before the market data
- Sales comp (variable-heavy) looks structurally different from engineering comp (equity-heavy)

These aren't bugs — they're part of the exercise.

---

## What You Build

Everything else. Specifically:

### 1. Tool Layer

Design and implement the **tools** your agent will use to access the comp data. This is a core design decision:

- What tools does an AI comp analyst need?
- What are the right abstractions? (One tool per data source? Higher-level analytical tools? Something else?)
- What should the tool interfaces look like for an LLM to use them effectively?
- How do you handle tool errors, missing data, and edge cases?

Your tools should wrap the fixture data, but design them as if they were calling real APIs.

### 2. Agent Architecture

Design and implement the **agent** — the reasoning and execution layer that takes a question, decides what to do, and produces an answer.

- How does the agent plan and execute? (ReAct loop? Plan-then-execute? Something else?)
- How does it handle multi-step questions that require chaining tool outputs?
- How does it handle ambiguity in the question?
- How does it handle contradictory signals in the data? (e.g., competitive by market but above band max)

### 3. Evaluation

Design and implement a way to **evaluate your agent's output quality.** This is intentionally open-ended — we want to see how you think about what "correct" means for a comp analyst agent. Consider:

- What does a good answer look like? What makes one answer better than another?
- How do you test that the agent calls the right tools with the right arguments?
- How do you test that the output is factually consistent with the underlying data?
- How do you test for the things that matter most in comp analysis — like surfacing uncertainty, handling ambiguity, and producing actionable recommendations?
- How would this eval approach scale as you add more capabilities?

---

## Constraints

- Use **Python 3.11+**
- You may use **any LLM provider**
- You may use **any libraries** you want
- **Time budget: 120 minutes.** We're not looking for production polish. We're looking for the quality of your design decisions. Cut scope deliberately and tell us what you cut and why.

---

## What to Submit

1. A zipped version of your code
2. A `DECISIONS.md` explaining:
   - Your tool design — what tools you created and why
   - Your agent architecture — how it works and what alternatives you considered
   - Your eval approach — what you test for and why
   - What you'd change or add with more time
   - Where you used AI assistance and where you didn't (we expect you to use tools like Copilot or Claude Code — we're evaluating your judgment about when AI help is and isn't sufficient)

---

## What Happens Next

You'll book a 60-minute session with one of our engineers. We'll:

- **Demo** — Run your agent on 3–4 queries live, including ones that stress your design choices.
- **Walk through** — Discuss your tool design, agent architecture, and eval approach in depth.
- **Extend** — Ask you to add a capability live
- **Discuss** — Talk about how this would evolve toward production: scale, reliability, permissions, multi-agent coordination.

---

## Getting Started

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your LLM API key
```

Browse the fixture data in `src/data/` to understand what you're working with. Then start building.
