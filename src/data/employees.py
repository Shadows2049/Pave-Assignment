# src/data/employees.py

from dataclasses import dataclass
from typing import Literal


@dataclass
class Comp:
    base: int
    equity: int  # annualized vest value
    bonus: int  # target bonus
    total_comp: int


@dataclass
class Performance:
    rating: Literal["exceptional", "exceeds", "meets", "developing", "below"]
    last_review_date: str
    summary: str


@dataclass
class Demographics:
    gender: Literal["M", "F", "NB"]
    ethnicity: str


@dataclass
class Employee:
    id: str
    name: str
    department: str
    role: str
    level: str
    location: str
    manager: str
    start_date: str
    comp: Comp
    performance: Performance
    demographics: Demographics


employees: list[Employee] = [
    # ── Engineering ────────────────────────────────────────────────────
    Employee(
        id="emp-001",
        name="Jamie Chen",
        department="Engineering",
        role="Software Engineer",
        level="L4",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2022-03-15",
        comp=Comp(base=165_000, equity=40_000, bonus=16_500, total_comp=221_500),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Consistently delivers ahead of schedule. Strong technical leadership on the data pipeline migration."),
        demographics=Demographics(gender="M", ethnicity="Asian"),
    ),
    Employee(
        id="emp-002",
        name="Priya Sharma",
        department="Engineering",
        role="Software Engineer",
        level="L4",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2021-08-01",
        comp=Comp(base=155_000, equity=35_000, bonus=15_500, total_comp=205_500),
        performance=Performance(rating="exceptional", last_review_date="2025-09-01", summary="Driving architecture for the new comp engine. Operating well above level — strong promotion candidate."),
        demographics=Demographics(gender="F", ethnicity="South Asian"),
    ),
    Employee(
        id="emp-003",
        name="Marcus Johnson",
        department="Engineering",
        role="Software Engineer",
        level="L5",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2020-01-10",
        comp=Comp(base=195_000, equity=80_000, bonus=29_250, total_comp=304_250),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Solid contributor. Reliable on execution but hasn't expanded scope as expected at L5."),
        demographics=Demographics(gender="M", ethnicity="Black"),
    ),
    Employee(
        id="emp-004",
        name="Sofia Rodriguez",
        department="Engineering",
        role="Software Engineer",
        level="L3",
        location="New York",
        manager="Dana Reeves",
        start_date="2024-06-01",
        comp=Comp(base=140_000, equity=20_000, bonus=14_000, total_comp=174_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Ramping well for first year. Solid fundamentals, needs more ownership of end-to-end projects."),
        demographics=Demographics(gender="F", ethnicity="Hispanic"),
    ),
    Employee(
        id="emp-005",
        name="Alex Kim",
        department="Engineering",
        role="Software Engineer",
        level="L5",
        location="New York",
        manager="Dana Reeves",
        start_date="2021-03-01",
        comp=Comp(base=185_000, equity=60_000, bonus=27_750, total_comp=272_750),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Excellent cross-team influence. Led the API platform initiative and mentors junior engineers."),
        demographics=Demographics(gender="NB", ethnicity="Asian"),
    ),
    Employee(
        id="emp-006",
        name="Tyler Washington",
        department="Engineering",
        role="Software Engineer",
        level="L4",
        location="Remote - US",
        manager="Dana Reeves",
        start_date="2023-01-15",
        comp=Comp(base=150_000, equity=30_000, bonus=15_000, total_comp=195_000),
        performance=Performance(rating="developing", last_review_date="2025-09-01", summary="Struggling with ambiguity at L4. Needs more structure and has missed several project milestones."),
        demographics=Demographics(gender="M", ethnicity="Black"),
    ),
    Employee(
        id="emp-007",
        name="Mei Lin",
        department="Engineering",
        role="Software Engineer",
        level="L6",
        location="San Francisco",
        manager="VP Engineering",
        start_date="2019-06-01",
        comp=Comp(base=230_000, equity=150_000, bonus=46_000, total_comp=426_000),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Technical leader across the org. Defined the agent architecture and mentors staff engineers."),
        demographics=Demographics(gender="F", ethnicity="Asian"),
    ),
    Employee(
        id="emp-008",
        name="Ryan O'Brien",
        department="Engineering",
        role="Software Engineer",
        level="L3",
        location="Remote - US",
        manager="Dana Reeves",
        start_date="2024-09-01",
        comp=Comp(base=125_000, equity=15_000, bonus=12_500, total_comp=152_500),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="New hire, too early for full assessment. Shows promise in code quality and testing."),
        demographics=Demographics(gender="M", ethnicity="White"),
    ),

    # ── Platform Engineering ───────────────────────────────────────────
    Employee(
        id="emp-009",
        name="Aisha Patel",
        department="Platform",
        role="Platform Engineer",
        level="L5",
        location="San Francisco",
        manager="Lucas Amaral",
        start_date="2020-11-01",
        comp=Comp(base=200_000, equity=85_000, bonus=30_000, total_comp=315_000),
        performance=Performance(rating="exceptional", last_review_date="2025-09-01", summary="Architected the MCP service layer. Driving platform-wide reliability initiatives. Clear L6 trajectory."),
        demographics=Demographics(gender="F", ethnicity="South Asian"),
    ),
    Employee(
        id="emp-010",
        name="Dmitri Volkov",
        department="Platform",
        role="Platform Engineer",
        level="L4",
        location="New York",
        manager="Lucas Amaral",
        start_date="2022-07-01",
        comp=Comp(base=170_000, equity=45_000, bonus=17_000, total_comp=232_000),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Strong infrastructure instincts. Owns the deploy pipeline and has meaningfully reduced incident rates."),
        demographics=Demographics(gender="M", ethnicity="White"),
    ),

    # ── Product ────────────────────────────────────────────────────────
    Employee(
        id="emp-011",
        name="Jordan Lee",
        department="Product",
        role="Product Manager",
        level="L5",
        location="San Francisco",
        manager="CPO",
        start_date="2021-05-01",
        comp=Comp(base=190_000, equity=70_000, bonus=38_000, total_comp=298_000),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Owns the comp planning product. Excellent at translating customer problems into product specs."),
        demographics=Demographics(gender="NB", ethnicity="Asian"),
    ),
    Employee(
        id="emp-012",
        name="Hannah Brooks",
        department="Product",
        role="Product Manager",
        level="L4",
        location="New York",
        manager="Jordan Lee",
        start_date="2023-02-01",
        comp=Comp(base=160_000, equity=35_000, bonus=24_000, total_comp=219_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Solid execution on market pricing features. Growing into more strategic thinking."),
        demographics=Demographics(gender="F", ethnicity="White"),
    ),
    Employee(
        id="emp-013",
        name="Carlos Mendez",
        department="Product",
        role="Product Manager",
        level="L4",
        location="Remote - US",
        manager="Jordan Lee",
        start_date="2023-08-01",
        comp=Comp(base=150_000, equity=30_000, bonus=22_500, total_comp=202_500),
        performance=Performance(rating="developing", last_review_date="2025-09-01", summary="Needs improvement on stakeholder management and prioritization rigor."),
        demographics=Demographics(gender="M", ethnicity="Hispanic"),
    ),

    # ── Design ─────────────────────────────────────────────────────────
    Employee(
        id="emp-014",
        name="Zara Mohammed",
        department="Design",
        role="Product Designer",
        level="L4",
        location="San Francisco",
        manager="Head of Design",
        start_date="2022-04-01",
        comp=Comp(base=155_000, equity=35_000, bonus=15_500, total_comp=205_500),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Strong systems thinker. Led the design system overhaul and improved design velocity across teams."),
        demographics=Demographics(gender="F", ethnicity="Middle Eastern"),
    ),
    Employee(
        id="emp-015",
        name="Ethan Park",
        department="Design",
        role="Product Designer",
        level="L3",
        location="New York",
        manager="Head of Design",
        start_date="2024-01-15",
        comp=Comp(base=120_000, equity=15_000, bonus=12_000, total_comp=147_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Good craft skills. Building confidence in leading design reviews independently."),
        demographics=Demographics(gender="M", ethnicity="Asian"),
    ),

    # ── Sales ──────────────────────────────────────────────────────────
    Employee(
        id="emp-016",
        name="Rachel Torres",
        department="Sales",
        role="Account Executive",
        level="L4",
        location="San Francisco",
        manager="VP Sales",
        start_date="2022-01-01",
        comp=Comp(base=130_000, equity=25_000, bonus=65_000, total_comp=220_000),
        performance=Performance(rating="exceptional", last_review_date="2025-09-01", summary="Top performer. 140% of quota. Closing enterprise deals and mentoring new AEs."),
        demographics=Demographics(gender="F", ethnicity="Hispanic"),
    ),
    Employee(
        id="emp-017",
        name="Ben Nakamura",
        department="Sales",
        role="Account Executive",
        level="L4",
        location="New York",
        manager="VP Sales",
        start_date="2023-03-01",
        comp=Comp(base=125_000, equity=20_000, bonus=55_000, total_comp=200_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Steady performer at 100% quota. Solid pipeline management."),
        demographics=Demographics(gender="M", ethnicity="Asian"),
    ),
    Employee(
        id="emp-018",
        name="Lisa Andersson",
        department="Sales",
        role="Account Executive",
        level="L3",
        location="Remote - US",
        manager="VP Sales",
        start_date="2024-04-01",
        comp=Comp(base=100_000, equity=10_000, bonus=40_000, total_comp=150_000),
        performance=Performance(rating="developing", last_review_date="2025-09-01", summary="At 60% of quota. Struggling with enterprise deal complexity. Needs coaching on multi-threading."),
        demographics=Demographics(gender="F", ethnicity="White"),
    ),

    # ── Customer Success ───────────────────────────────────────────────
    Employee(
        id="emp-019",
        name="David Kim",
        department="Customer Success",
        role="Customer Success Manager",
        level="L4",
        location="San Francisco",
        manager="VP CS",
        start_date="2021-09-01",
        comp=Comp(base=140_000, equity=30_000, bonus=21_000, total_comp=191_000),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Highest NPS in the org. Manages key enterprise accounts and drives expansion revenue."),
        demographics=Demographics(gender="M", ethnicity="Asian"),
    ),
    Employee(
        id="emp-020",
        name="Olivia Chen",
        department="Customer Success",
        role="Customer Success Manager",
        level="L3",
        location="Remote - US",
        manager="VP CS",
        start_date="2024-02-01",
        comp=Comp(base=105_000, equity=12_000, bonus=15_750, total_comp=132_750),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Growing well. Good customer rapport but needs to develop more strategic account planning skills."),
        demographics=Demographics(gender="F", ethnicity="Asian"),
    ),

    # ── Data Science ───────────────────────────────────────────────────
    Employee(
        id="emp-021",
        name="Nadia Okafor",
        department="Data Science",
        role="Data Scientist",
        level="L5",
        location="San Francisco",
        manager="VP Engineering",
        start_date="2020-08-01",
        comp=Comp(base=205_000, equity=90_000, bonus=30_750, total_comp=325_750),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Built the market pricing models. Leads the ML team and drives data strategy across the product."),
        demographics=Demographics(gender="F", ethnicity="Black"),
    ),
    Employee(
        id="emp-022",
        name="Sam Patel",
        department="Data Science",
        role="Data Scientist",
        level="L4",
        location="New York",
        manager="Nadia Okafor",
        start_date="2023-05-01",
        comp=Comp(base=170_000, equity=40_000, bonus=25_500, total_comp=235_500),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Strong technical skills. Needs to develop more product intuition about what analyses matter most."),
        demographics=Demographics(gender="M", ethnicity="South Asian"),
    ),

    # ── Additional Engineers ───────────────────────────────────────────
    Employee(
        id="emp-023",
        name="Emma Wilson",
        department="Engineering",
        role="Software Engineer",
        level="L4",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2022-10-01",
        comp=Comp(base=158_000, equity=38_000, bonus=15_800, total_comp=211_800),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Excellent full-stack engineer. Led the new onboarding flow and reduced time-to-value by 30%."),
        demographics=Demographics(gender="F", ethnicity="White"),
    ),
    Employee(
        id="emp-024",
        name="Kevin Tran",
        department="Engineering",
        role="Software Engineer",
        level="L4",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2021-11-01",
        comp=Comp(base=148_000, equity=32_000, bonus=14_800, total_comp=194_800),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Dependable contributor. Solid on execution, could take on more technical leadership."),
        demographics=Demographics(gender="M", ethnicity="Asian"),
    ),
    Employee(
        id="emp-025",
        name="Maya Gupta",
        department="Engineering",
        role="Software Engineer",
        level="L5",
        location="Remote - US",
        manager="Dana Reeves",
        start_date="2020-05-01",
        comp=Comp(base=180_000, equity=55_000, bonus=27_000, total_comp=262_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Consistent performer. Owns the reporting pipeline but scope hasn't expanded at L5."),
        demographics=Demographics(gender="F", ethnicity="South Asian"),
    ),
    Employee(
        id="emp-026",
        name="Chris Larsen",
        department="Engineering",
        role="Software Engineer",
        level="L3",
        location="San Francisco",
        manager="Dana Reeves",
        start_date="2024-07-15",
        comp=Comp(base=135_000, equity=18_000, bonus=13_500, total_comp=166_500),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Fast learner. Already contributing independently and showing strong debugging instincts."),
        demographics=Demographics(gender="M", ethnicity="White"),
    ),

    # ── More Platform ──────────────────────────────────────────────────
    Employee(
        id="emp-027",
        name="Fatima Al-Hassan",
        department="Platform",
        role="Platform Engineer",
        level="L4",
        location="San Francisco",
        manager="Lucas Amaral",
        start_date="2023-03-01",
        comp=Comp(base=168_000, equity=42_000, bonus=16_800, total_comp=226_800),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="Reliable on infrastructure work. Building expertise in observability."),
        demographics=Demographics(gender="F", ethnicity="Middle Eastern"),
    ),
    Employee(
        id="emp-028",
        name="Jake Morrison",
        department="Platform",
        role="Platform Engineer",
        level="L3",
        location="Remote - US",
        manager="Lucas Amaral",
        start_date="2024-08-01",
        comp=Comp(base=130_000, equity=18_000, bonus=13_000, total_comp=161_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="New hire. Adapting to the codebase. Showing good initiative on documentation."),
        demographics=Demographics(gender="M", ethnicity="White"),
    ),

    # ── More Sales ─────────────────────────────────────────────────────
    Employee(
        id="emp-029",
        name="Nina Kowalski",
        department="Sales",
        role="Account Executive",
        level="L5",
        location="San Francisco",
        manager="VP Sales",
        start_date="2020-06-01",
        comp=Comp(base=155_000, equity=45_000, bonus=95_000, total_comp=295_000),
        performance=Performance(rating="exceeds", last_review_date="2025-09-01", summary="Enterprise closer. 125% of quota. Building out the strategic accounts playbook."),
        demographics=Demographics(gender="F", ethnicity="White"),
    ),
    Employee(
        id="emp-030",
        name="Andre Williams",
        department="Sales",
        role="Sales Development Rep",
        level="L2",
        location="New York",
        manager="VP Sales",
        start_date="2024-10-01",
        comp=Comp(base=75_000, equity=5_000, bonus=25_000, total_comp=105_000),
        performance=Performance(rating="meets", last_review_date="2025-09-01", summary="New to role. Hitting activity metrics. Needs to improve discovery call quality."),
        demographics=Demographics(gender="M", ethnicity="Black"),
    ),
]
