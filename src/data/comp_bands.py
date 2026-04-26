# src/data/comp_bands.py

from dataclasses import dataclass
from typing import Literal


@dataclass
class CompBand:
    role: str
    level: str
    component: Literal["base", "equity", "bonus", "total_comp"]
    min: int
    mid: int
    max: int
    updated_at: str


comp_bands: list[CompBand] = [
    # ── Software Engineer ──────────────────────────────────────────────
    CompBand(role="Software Engineer", level="L3", component="base", min=120_000, mid=140_000, max=160_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L3", component="equity", min=12_000, mid=22_000, max=35_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L3", component="total_comp", min=145_000, mid=175_000, max=210_000, updated_at="2025-07-01"),

    CompBand(role="Software Engineer", level="L4", component="base", min=150_000, mid=170_000, max=195_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L4", component="equity", min=28_000, mid=45_000, max=70_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L4", component="total_comp", min=195_000, mid=235_000, max=285_000, updated_at="2025-07-01"),

    CompBand(role="Software Engineer", level="L5", component="base", min=180_000, mid=205_000, max=235_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L5", component="equity", min=55_000, mid=85_000, max=130_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L5", component="total_comp", min=265_000, mid=325_000, max=400_000, updated_at="2025-07-01"),

    CompBand(role="Software Engineer", level="L6", component="base", min=215_000, mid=245_000, max=280_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L6", component="equity", min=110_000, mid=170_000, max=250_000, updated_at="2025-07-01"),
    CompBand(role="Software Engineer", level="L6", component="total_comp", min=370_000, mid=465_000, max=580_000, updated_at="2025-07-01"),

    # ── Platform Engineer ──────────────────────────────────────────────
    CompBand(role="Platform Engineer", level="L3", component="base", min=120_000, mid=140_000, max=160_000, updated_at="2025-07-01"),
    CompBand(role="Platform Engineer", level="L3", component="total_comp", min=145_000, mid=175_000, max=210_000, updated_at="2025-07-01"),

    CompBand(role="Platform Engineer", level="L4", component="base", min=155_000, mid=175_000, max=200_000, updated_at="2025-07-01"),
    CompBand(role="Platform Engineer", level="L4", component="total_comp", min=205_000, mid=250_000, max=300_000, updated_at="2025-07-01"),

    CompBand(role="Platform Engineer", level="L5", component="base", min=185_000, mid=215_000, max=245_000, updated_at="2025-07-01"),
    CompBand(role="Platform Engineer", level="L5", component="total_comp", min=285_000, mid=350_000, max=425_000, updated_at="2025-07-01"),

    # ── Product Manager ────────────────────────────────────────────────
    CompBand(role="Product Manager", level="L4", component="base", min=145_000, mid=165_000, max=190_000, updated_at="2025-07-01"),
    CompBand(role="Product Manager", level="L4", component="total_comp", min=195_000, mid=240_000, max=290_000, updated_at="2025-07-01"),

    CompBand(role="Product Manager", level="L5", component="base", min=175_000, mid=200_000, max=230_000, updated_at="2025-07-01"),
    CompBand(role="Product Manager", level="L5", component="total_comp", min=265_000, mid=330_000, max=400_000, updated_at="2025-07-01"),

    # ── Product Designer ───────────────────────────────────────────────
    CompBand(role="Product Designer", level="L3", component="base", min=105_000, mid=122_000, max=140_000, updated_at="2025-07-01"),
    CompBand(role="Product Designer", level="L3", component="total_comp", min=128_000, mid=155_000, max=185_000, updated_at="2025-07-01"),

    CompBand(role="Product Designer", level="L4", component="base", min=138_000, mid=158_000, max=180_000, updated_at="2025-07-01"),
    CompBand(role="Product Designer", level="L4", component="total_comp", min=185_000, mid=225_000, max=270_000, updated_at="2025-07-01"),

    # ── Account Executive ──────────────────────────────────────────────
    CompBand(role="Account Executive", level="L3", component="base", min=80_000, mid=100_000, max=118_000, updated_at="2025-07-01"),
    CompBand(role="Account Executive", level="L3", component="total_comp", min=125_000, mid=160_000, max=200_000, updated_at="2025-07-01"),

    CompBand(role="Account Executive", level="L4", component="base", min=115_000, mid=135_000, max=158_000, updated_at="2025-07-01"),
    CompBand(role="Account Executive", level="L4", component="total_comp", min=195_000, mid=245_000, max=310_000, updated_at="2025-07-01"),

    CompBand(role="Account Executive", level="L5", component="base", min=140_000, mid=162_000, max=185_000, updated_at="2025-07-01"),
    CompBand(role="Account Executive", level="L5", component="total_comp", min=265_000, mid=325_000, max=400_000, updated_at="2025-07-01"),

    # ── Customer Success Manager ───────────────────────────────────────
    CompBand(role="Customer Success Manager", level="L3", component="base", min=82_000, mid=98_000, max=115_000, updated_at="2025-07-01"),
    CompBand(role="Customer Success Manager", level="L3", component="total_comp", min=100_000, mid=125_000, max=152_000, updated_at="2025-07-01"),

    CompBand(role="Customer Success Manager", level="L4", component="base", min=120_000, mid=142_000, max=165_000, updated_at="2025-07-01"),
    CompBand(role="Customer Success Manager", level="L4", component="total_comp", min=160_000, mid=195_000, max=235_000, updated_at="2025-07-01"),

    # ── Data Scientist ─────────────────────────────────────────────────
    CompBand(role="Data Scientist", level="L4", component="base", min=152_000, mid=172_000, max=195_000, updated_at="2025-07-01"),
    CompBand(role="Data Scientist", level="L4", component="total_comp", min=205_000, mid=250_000, max=300_000, updated_at="2025-07-01"),

    CompBand(role="Data Scientist", level="L5", component="base", min=188_000, mid=215_000, max=248_000, updated_at="2025-07-01"),
    CompBand(role="Data Scientist", level="L5", component="total_comp", min=285_000, mid=355_000, max=435_000, updated_at="2025-07-01"),

    # ── Sales Development Rep ──────────────────────────────────────────
    CompBand(role="Sales Development Rep", level="L2", component="base", min=58_000, mid=72_000, max=88_000, updated_at="2025-07-01"),
    CompBand(role="Sales Development Rep", level="L2", component="total_comp", min=80_000, mid=102_000, max=128_000, updated_at="2025-07-01"),
]
