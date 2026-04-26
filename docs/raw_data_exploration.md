Now I have a thorough picture of everything. Here's a complete breakdown:

---

## Project Goal

Build **Paige** — an AI compensation analyst agent that answers natural language questions about employee compensation by reasoning over three structured datasets. The agent must handle everything from simple lookups to multi-step analysis to genuinely ambiguous questions.

---

## The Six Target Questions (Increasing Complexity)

| # | Question | Type |
|---|----------|------|
| 1 | "Is Jamie Chen's total comp competitive?" | Point lookup + market comparison |
| 2 | "Who on the engineering team is most at risk of attrition due to comp?" | Multi-employee analysis, ranking |
| 3 | "Compare our L5 engineer pay to market across all locations." | Cross-location aggregation |
| 4 | "We're promoting Priya Sharma to L5. What should her new comp package look like?" | Recommendation + multi-source synthesis |
| 5 | "Which department has the biggest gap between internal comp and market rates?" | Full-org scan, comparison, ranking |
| 6 | "Are there any pay equity concerns I should know about on the platform team?" | Statistical analysis + demographic awareness |

---

## Data Schema & Relationships

### `employees.py` — 30 employees

```
Employee
├── id, name, department, role, level, location, manager, start_date
├── Comp        → base, equity (annualized vest), bonus (target), total_comp
├── Performance → rating [exceptional|exceeds|meets|developing|below], last_review_date, summary
└── Demographics → gender [M|F|NB], ethnicity
```

**7 departments, 8 roles, 5 levels (L2–L6), 3 locations:**

| Department | Employees | Roles |
|---|---|---|
| Engineering | 12 | Software Engineer (L3–L6) |
| Platform | 4 | Platform Engineer (L3–L5) |
| Product | 3 | Product Manager (L4–L5) |
| Design | 2 | Product Designer (L3–L4) |
| Sales | 5 | Account Executive (L3–L5), SDR (L2) |
| Customer Success | 2 | Customer Success Manager (L3–L4) |
| Data Science | 2 | Data Scientist (L4–L5) |

**Join key → Market Data:** `role + level + location`
**Join key → Comp Bands:** `role + level`

---

### `market_data.py` — External benchmarks

```
MarketBenchmark
├── role, level, location   ← join key
├── component               ← "base" | "equity" | "bonus" | "total_comp"
├── p25, p50, p75, p90      ← percentile anchors
├── sample_size             ← 67 to 456 (varies widely — confidence signal)
└── updated_at              ← all 2025-10-01
```

Covers: Software Engineer, Platform Engineer, Product Manager, Product Designer, Account Executive, Customer Success Manager, Data Scientist, Sales Development Rep — but **not uniformly**. Some role/level/location combos are missing entirely.

---

### `comp_bands.py` — Internal pay ranges

```
CompBand
├── role, level             ← join key (national, no location dimension)
├── component               ← "base" | "equity" | "bonus" | "total_comp"
├── min, mid, max           ← the band range
└── updated_at              ← all 2025-07-01 (3 months stale vs market data)
```

---

## Intentional Data Problems (The Real Challenge)

The exercise embeds realistic messiness. Here's what's actually in the data:

### 1. Missing market data
- **Platform Engineer at Remote-US**: zero market benchmarks → Jake Morrison (L3, Remote) has no market comp data at all
- **Platform Engineer L3**: no market data at any location
- **Some components missing**: e.g., no equity benchmark for L4 SWE NY/Remote, no bonus data for most roles

### 2. Bands are national, market is location-specific
- The `comp_bands` have no location dimension — they're one-size-fits-all
- Employees in SF face a higher market than the national band implies
- Comparing a SF employee's pay to their "band" vs. "SF market" gives different answers

### 3. Employees outside their bands
- **Kevin Tran** (L4 SWE SF): `base=$148k` vs band min `$150k` → below band floor
- **Priya Sharma** (L4 SWE SF): `total_comp=$205.5k` vs market `p25=$210k` → below market p25, and she's rated *exceptional*

### 4. Contradictory signals
- Mei Lin (L6 SWE SF): `total_comp=$426k` → above band max ($580k is max, she's mid-band), "exceeds" performer — seems fine
- But her `total_comp=$426k` vs market `p50=$480k` → she's actually below market median for her level despite looking well-paid

### 5. Sales comp is structurally different
- Rachel Torres (AE L4 SF): `base=$130k, bonus=$65k` — the bonus is 50% of base
- Comparing AE total comp to market is valid, but the base-only view is misleading
- Rachel is at 140% quota but her total_comp ($220k) sits at market p25 ($200k) → potentially a flight risk

### 6. Pay equity signals
Looking at L4 Software Engineers in San Francisco — same role, level, location:

| Employee | Gender | Perf | Base |
|---|---|---|---|
| Kevin Tran | M | meets | $148k |
| Priya Sharma | F | **exceptional** | $155k |
| Emma Wilson | F | exceeds | $158k |
| Jamie Chen | M | exceeds | $165k |

Priya (exceptional) earns less than Jamie (exceeds, same rating tier below hers). This is the kind of pay equity signal the agent must surface.

### 7. Band staleness
- Bands updated `2025-07-01`, market data `2025-10-01` — 3 months drift means bands may understate current market rates

---

## What the Agent Needs to Reason About

To answer the six questions, the agent must chain across all three datasets:

```
Question
  └─► identify employee(s)          [employees]
        └─► get their comp           [employees.comp]
              └─► compare to market  [market_data @ role+level+location]
                    └─► compare to band [comp_bands @ role+level]
                          └─► factor in performance, demographics, tenure
                                └─► synthesize answer + flag uncertainty
```

The hard part isn't data retrieval — it's **judgment**: knowing when market data is thin (low confidence), when band-vs-market conflicts, when performance/comp are misaligned, and when to flag "I can't fully answer this because data is missing."
