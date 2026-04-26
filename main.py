#!/usr/bin/env python3
"""
CLI entry: compensation analyst agent (LangGraph: supervisor → executor → reducer).

Usage:
  source venv/bin/activate
  export OPENAI_API_KEY=...  # or set in .env
  python main.py "Is Jamie Chen's total comp competitive?"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.agent.graph import run_query


def main() -> int:
    p = argparse.ArgumentParser(description="Paige comp analyst (MVP)")
    p.add_argument("query", help="Natural language comp question")
    p.add_argument("--json", action="store_true", help="Print full state JSON (debug)")
    p.add_argument(
        "--model", default="gpt-4.1-mini", help="OpenAI model id (default: gpt-4.1-mini)"
    )
    p.add_argument(
        "--no-save",
        action="store_true",
        help="Do not write output/runs/summary.md and trace files",
    )
    p.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Override output folder (default: output/runs or PAIGE_OUTPUT_DIR)",
    )
    args = p.parse_args()
    out = run_query(
        args.query,
        model=args.model,
        save_artifacts=not args.no_save,
        output_root=args.output_root,
    )
    if args.json:
        # Avoid non-serializable message objects
        d = {k: v for k, v in out.items() if k != "messages"}
        print(json.dumps(d, default=str, indent=2))
        return 0
    print(out.get("final_answer") or "(no final_answer)")
    if out.get("run_dir") and not args.no_save:
        ap = out.get("artifact_paths") or {}
        print(f"\nSaved: summary={ap.get('summary_md')} trace_json={ap.get('trace_json')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
