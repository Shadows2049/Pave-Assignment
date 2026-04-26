# src/data/market_data.py

from dataclasses import dataclass
from typing import Literal


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
    sample_size: int
    updated_at: str


market_data: list[MarketBenchmark] = [
    # ── Software Engineer ──────────────────────────────────────────────
    # L3
    MarketBenchmark(role="Software Engineer", level="L3", location="San Francisco", component="base", p25=130_000, p50=145_000, p75=160_000, p90=175_000, sample_size=342, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="San Francisco", component="equity", p25=15_000, p50=25_000, p75=40_000, p90=55_000, sample_size=342, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="San Francisco", component="total_comp", p25=160_000, p50=185_000, p75=215_000, p90=245_000, sample_size=342, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="New York", component="base", p25=125_000, p50=140_000, p75=155_000, p90=170_000, sample_size=289, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="New York", component="equity", p25=12_000, p50=22_000, p75=35_000, p90=50_000, sample_size=289, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="New York", component="total_comp", p25=150_000, p50=175_000, p75=205_000, p90=235_000, sample_size=289, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="Remote - US", component="base", p25=115_000, p50=130_000, p75=145_000, p90=158_000, sample_size=198, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L3", location="Remote - US", component="total_comp", p25=140_000, p50=165_000, p75=195_000, p90=220_000, sample_size=198, updated_at="2025-10-01"),

    # L4
    MarketBenchmark(role="Software Engineer", level="L4", location="San Francisco", component="base", p25=155_000, p50=175_000, p75=195_000, p90=210_000, sample_size=456, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="San Francisco", component="equity", p25=30_000, p50=50_000, p75=75_000, p90=100_000, sample_size=456, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="San Francisco", component="bonus", p25=12_000, p50=18_000, p75=25_000, p90=32_000, sample_size=456, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="San Francisco", component="total_comp", p25=210_000, p50=250_000, p75=295_000, p90=340_000, sample_size=456, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="New York", component="base", p25=150_000, p50=170_000, p75=190_000, p90=205_000, sample_size=378, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="New York", component="total_comp", p25=200_000, p50=240_000, p75=285_000, p90=330_000, sample_size=378, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="Remote - US", component="base", p25=140_000, p50=158_000, p75=178_000, p90=195_000, sample_size=267, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L4", location="Remote - US", component="total_comp", p25=185_000, p50=225_000, p75=270_000, p90=310_000, sample_size=267, updated_at="2025-10-01"),

    # L5
    MarketBenchmark(role="Software Engineer", level="L5", location="San Francisco", component="base", p25=185_000, p50=210_000, p75=235_000, p90=255_000, sample_size=234, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="San Francisco", component="equity", p25=60_000, p50=95_000, p75=140_000, p90=190_000, sample_size=234, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="San Francisco", component="total_comp", p25=280_000, p50=340_000, p75=410_000, p90=480_000, sample_size=234, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="New York", component="base", p25=180_000, p50=205_000, p75=230_000, p90=250_000, sample_size=187, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="New York", component="total_comp", p25=270_000, p50=330_000, p75=400_000, p90=470_000, sample_size=187, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="Remote - US", component="base", p25=170_000, p50=192_000, p75=218_000, p90=240_000, sample_size=156, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L5", location="Remote - US", component="total_comp", p25=250_000, p50=310_000, p75=380_000, p90=445_000, sample_size=156, updated_at="2025-10-01"),

    # L6
    MarketBenchmark(role="Software Engineer", level="L6", location="San Francisco", component="base", p25=220_000, p50=250_000, p75=280_000, p90=310_000, sample_size=89, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L6", location="San Francisco", component="equity", p25=120_000, p50=180_000, p75=260_000, p90=350_000, sample_size=89, updated_at="2025-10-01"),
    MarketBenchmark(role="Software Engineer", level="L6", location="San Francisco", component="total_comp", p25=390_000, p50=480_000, p75=590_000, p90=710_000, sample_size=89, updated_at="2025-10-01"),

    # ── Platform Engineer (intentionally thinner data) ─────────────────
    MarketBenchmark(role="Platform Engineer", level="L4", location="San Francisco", component="base", p25=160_000, p50=180_000, p75=200_000, p90=218_000, sample_size=124, updated_at="2025-10-01"),
    MarketBenchmark(role="Platform Engineer", level="L4", location="San Francisco", component="total_comp", p25=220_000, p50=265_000, p75=310_000, p90=355_000, sample_size=124, updated_at="2025-10-01"),
    MarketBenchmark(role="Platform Engineer", level="L4", location="New York", component="base", p25=155_000, p50=175_000, p75=195_000, p90=212_000, sample_size=87, updated_at="2025-10-01"),
    MarketBenchmark(role="Platform Engineer", level="L4", location="New York", component="total_comp", p25=210_000, p50=255_000, p75=300_000, p90=340_000, sample_size=87, updated_at="2025-10-01"),
    MarketBenchmark(role="Platform Engineer", level="L5", location="San Francisco", component="base", p25=195_000, p50=220_000, p75=245_000, p90=265_000, sample_size=67, updated_at="2025-10-01"),
    MarketBenchmark(role="Platform Engineer", level="L5", location="San Francisco", component="total_comp", p25=300_000, p50=365_000, p75=435_000, p90=510_000, sample_size=67, updated_at="2025-10-01"),
    # NOTE: No Remote - US data for Platform Engineers — intentional gap

    # ── Product Manager ────────────────────────────────────────────────
    MarketBenchmark(role="Product Manager", level="L4", location="San Francisco", component="base", p25=150_000, p50=170_000, p75=190_000, p90=208_000, sample_size=198, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L4", location="San Francisco", component="total_comp", p25=205_000, p50=250_000, p75=295_000, p90=340_000, sample_size=198, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L4", location="New York", component="base", p25=145_000, p50=165_000, p75=185_000, p90=202_000, sample_size=156, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L4", location="New York", component="total_comp", p25=195_000, p50=240_000, p75=285_000, p90=325_000, sample_size=156, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L4", location="Remote - US", component="base", p25=135_000, p50=155_000, p75=175_000, p90=192_000, sample_size=112, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L4", location="Remote - US", component="total_comp", p25=180_000, p50=220_000, p75=265_000, p90=305_000, sample_size=112, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L5", location="San Francisco", component="base", p25=180_000, p50=205_000, p75=230_000, p90=250_000, sample_size=112, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Manager", level="L5", location="San Francisco", component="total_comp", p25=275_000, p50=335_000, p75=400_000, p90=465_000, sample_size=112, updated_at="2025-10-01"),

    # ── Product Designer ───────────────────────────────────────────────
    MarketBenchmark(role="Product Designer", level="L3", location="New York", component="base", p25=110_000, p50=125_000, p75=140_000, p90=155_000, sample_size=134, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Designer", level="L3", location="New York", component="total_comp", p25=135_000, p50=158_000, p75=185_000, p90=210_000, sample_size=134, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Designer", level="L4", location="San Francisco", component="base", p25=140_000, p50=160_000, p75=180_000, p90=198_000, sample_size=156, updated_at="2025-10-01"),
    MarketBenchmark(role="Product Designer", level="L4", location="San Francisco", component="total_comp", p25=190_000, p50=230_000, p75=275_000, p90=315_000, sample_size=156, updated_at="2025-10-01"),

    # ── Account Executive ──────────────────────────────────────────────
    MarketBenchmark(role="Account Executive", level="L3", location="Remote - US", component="base", p25=85_000, p50=100_000, p75=115_000, p90=128_000, sample_size=201, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L3", location="Remote - US", component="total_comp", p25=130_000, p50=165_000, p75=200_000, p90=240_000, sample_size=201, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L4", location="San Francisco", component="base", p25=120_000, p50=140_000, p75=158_000, p90=175_000, sample_size=178, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L4", location="San Francisco", component="total_comp", p25=200_000, p50=250_000, p75=310_000, p90=370_000, sample_size=178, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L4", location="New York", component="base", p25=115_000, p50=135_000, p75=153_000, p90=170_000, sample_size=145, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L4", location="New York", component="total_comp", p25=190_000, p50=240_000, p75=300_000, p90=355_000, sample_size=145, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L5", location="San Francisco", component="base", p25=145_000, p50=165_000, p75=185_000, p90=205_000, sample_size=78, updated_at="2025-10-01"),
    MarketBenchmark(role="Account Executive", level="L5", location="San Francisco", component="total_comp", p25=270_000, p50=330_000, p75=400_000, p90=480_000, sample_size=78, updated_at="2025-10-01"),

    # ── Customer Success Manager ───────────────────────────────────────
    MarketBenchmark(role="Customer Success Manager", level="L3", location="Remote - US", component="base", p25=85_000, p50=100_000, p75=115_000, p90=128_000, sample_size=145, updated_at="2025-10-01"),
    MarketBenchmark(role="Customer Success Manager", level="L3", location="Remote - US", component="total_comp", p25=105_000, p50=128_000, p75=152_000, p90=175_000, sample_size=145, updated_at="2025-10-01"),
    MarketBenchmark(role="Customer Success Manager", level="L4", location="San Francisco", component="base", p25=125_000, p50=145_000, p75=165_000, p90=180_000, sample_size=112, updated_at="2025-10-01"),
    MarketBenchmark(role="Customer Success Manager", level="L4", location="San Francisco", component="total_comp", p25=165_000, p50=200_000, p75=238_000, p90=270_000, sample_size=112, updated_at="2025-10-01"),

    # ── Data Scientist ─────────────────────────────────────────────────
    MarketBenchmark(role="Data Scientist", level="L4", location="New York", component="base", p25=155_000, p50=175_000, p75=195_000, p90=212_000, sample_size=134, updated_at="2025-10-01"),
    MarketBenchmark(role="Data Scientist", level="L4", location="New York", component="total_comp", p25=210_000, p50=255_000, p75=305_000, p90=350_000, sample_size=134, updated_at="2025-10-01"),
    MarketBenchmark(role="Data Scientist", level="L5", location="San Francisco", component="base", p25=190_000, p50=215_000, p75=245_000, p90=270_000, sample_size=89, updated_at="2025-10-01"),
    MarketBenchmark(role="Data Scientist", level="L5", location="San Francisco", component="equity", p25=65_000, p50=100_000, p75=150_000, p90=200_000, sample_size=89, updated_at="2025-10-01"),
    MarketBenchmark(role="Data Scientist", level="L5", location="San Francisco", component="total_comp", p25=290_000, p50=360_000, p75=440_000, p90=520_000, sample_size=89, updated_at="2025-10-01"),

    # ── Sales Development Rep (thin data) ──────────────────────────────
    MarketBenchmark(role="Sales Development Rep", level="L2", location="New York", component="base", p25=60_000, p50=72_000, p75=85_000, p90=95_000, sample_size=89, updated_at="2025-10-01"),
    MarketBenchmark(role="Sales Development Rep", level="L2", location="New York", component="total_comp", p25=85_000, p50=105_000, p75=128_000, p90=150_000, sample_size=89, updated_at="2025-10-01"),
]
