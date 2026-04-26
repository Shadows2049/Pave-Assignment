# src/agent/artifacts.py
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage


@dataclass
class LLMTokenLedger:
    """Aggregates OpenAI token_usage from each on_llm_end call."""

    calls: list[dict[str, Any]] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "per_call": self.calls,
            "totals": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "total_tokens": self.total_tokens,
            },
        }

    def on_llm_end_payload(self, response: Any, llm: dict[str, Any] | None = None) -> None:
        usage: dict[str, int] | None = None
        try:
            for gen_list in response.generations or []:
                for gen in gen_list:
                    msg = getattr(gen, "message", None)
                    if msg is not None:
                        rm = getattr(msg, "response_metadata", None) or {}
                        u = rm.get("token_usage")
                        if u:
                            usage = u
                            break
        except Exception:
            pass
        if not usage and llm and isinstance(llm, dict) and "token_usage" in (llm or {}):
            usage = llm.get("token_usage")
        if not usage:
            return
        it = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        ot = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        tt = int(usage.get("total_tokens") or (it + ot))
        self.total_input_tokens += it
        self.total_output_tokens += ot
        self.total_tokens += tt
        self.calls.append(
            {
                "input_tokens": it,
                "output_tokens": ot,
                "total_tokens": tt,
                "raw": usage,
            }
        )


class _TokenHandler(BaseCallbackHandler):
    def __init__(self, ledger: LLMTokenLedger) -> None:
        super().__init__()
        self._ledger = ledger

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:  # noqa: ANN401
        self._ledger.on_llm_end_payload(
            response,
            (kwargs.get("llm_output") or kwargs.get("response")),
        )


def make_token_handler(ledger: LLMTokenLedger) -> BaseCallbackHandler:
    return _TokenHandler(ledger)


def message_to_dict(m: Any) -> dict[str, Any] | str:
    if isinstance(m, BaseMessage):
        d: dict[str, Any] = {
            "type": m.type,
            "content": m.content
            if isinstance(m.content, str)
            else str(m.content)[:2000],
        }
        if getattr(m, "response_metadata", None):
            d["response_metadata"] = dict(m.response_metadata)  # may include token_usage
        return d
    return str(m)[:2000]


def state_to_jsonable(state: Any) -> dict[str, Any]:
    if not isinstance(state, dict):
        return {"_repr": str(state)[:5000]}

    out: dict[str, Any] = {}
    for k, v in state.items():
        if k == "messages" and isinstance(v, list):
            out[k] = [message_to_dict(x) for x in v]
        elif k == "tasks" and isinstance(v, list):
            out[k] = [_jsonable_task(t) for t in v]
        else:
            try:
                json.dumps(v, default=str)
                out[k] = v
            except TypeError:
                out[k] = str(v)[:5000]
    return out


def _jsonable_task(t: Any) -> dict[str, Any]:
    if not isinstance(t, dict):
        return {"_repr": str(t)}
    d = dict(t)
    r = d.get("result")
    if r is not None and not isinstance(r, (str, int, float, bool, type(None))):
        try:
            json.dumps(r, default=str)
        except TypeError:
            d["result"] = str(r)[:8000]
    return d


def _slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", s.strip())[:40]
    return s or "run"


def write_run_artifacts(
    *,
    run_dir: Path,
    run_id: str,
    model: str,
    original_query: str,
    started_at: str,
    finished_at: str,
    duration_s: float,
    final_state: dict[str, Any],
    trace_steps: list[dict[str, Any]],
    token_ledger: LLMTokenLedger,
    plan_approved: bool | None = None,
) -> dict[str, str]:
    run_dir = run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks = final_state.get("tasks") or []
    final_answer = final_state.get("final_answer") or ""
    main_objective = final_state.get("main_objective") or ""
    ctx = final_state.get("context") or ""

    # --- summary.md: answer + explicit tools & references
    tools_lines = []
    ref_lines: list[str] = []
    for t in tasks:
        tn = t.get("tool_name", "")
        tid = t.get("task_id", "")
        p = t.get("params")
        st = t.get("status", "")
        res = t.get("result") or {}
        src = res.get("source") if isinstance(res, dict) else None
        err = t.get("error")
        rtry = t.get("retries", 0)
        line = f"- **{tn}** (`{tid}`) status={st} retries={rtry} params={json.dumps(p, default=str)[:500]}"
        if src:
            line += f" → source=`{src}`"
        if err:
            e_short = (err[:200] + "…") if len(err) > 200 else err
            line += f" error={e_short!r}"
        tools_lines.append(line)
        if src and str(src) not in ref_lines:
            ref_lines.append(str(src))
        if isinstance(res, dict) and (md := res.get("metadata", {}).get("dataset")):
            s = f"{res.get('source')} / {md}"
            if s not in ref_lines:
                ref_lines.append(s)

    tot = token_ledger.to_dict()["totals"]
    plan_line = f"plan_approved: {plan_approved}" if plan_approved is not None else "plan_approved: unknown"
    meta = "\n".join(
        [
            "---",
            f"run_id: {run_id}",
            f"model: {model}",
            plan_line,
            f"started_at: {started_at}",
            f"finished_at: {finished_at}",
            f"duration_s: {duration_s:.3f}",
            f"tokens_aggregated: input={tot['input_tokens']} output={tot['output_tokens']} total={tot['total_tokens']}",
            "artifacts: summary.md, trace.json, trace.log, plan.json, plan.md (same folder)",
            "---",
        ]
    )
    body = [
        "# Comp analyst result",
        "",
        "## User question",
        "",
        f"> {original_query}",
        "",
        "## Objectives (supervisor)",
        "",
        f"**Main objective:** {main_objective}",
        "",
        f"**Context:** {ctx}",
        "",
        "## Model output",
        "",
        final_answer,
        "",
        "## Execution trace (tool calls, params, retries, sources)",
        "",
        *tools_lines,
        "",
        "## Datasets referenced (from tool `source` fields)",
        "",
        *([f"- {r}" for r in ref_lines] if ref_lines else ["- (none collected)"]),
        "",
        f"_Artifacts: `summary.md` (this file), `trace.json`, `trace.log` in `{run_dir}`_",
    ]
    summary_path = run_dir / "summary.md"
    summary_path.write_text(meta + "\n" + "\n".join(body), encoding="utf-8")

    # --- trace.json
    payload = {
        "run_id": run_id,
        "model": model,
        "original_query": original_query,
        "plan_approved": plan_approved,
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_s": duration_s,
        "token_usage": token_ledger.to_dict(),
        "trace_steps": trace_steps,
        "final_state": state_to_jsonable(final_state),
    }
    trace_json_path = run_dir / "trace.json"
    trace_json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    # --- trace.log (human-readable)
    log_lines = [
        f"=== run {run_id} ===",
        f"started: {started_at} finished: {finished_at} duration_s: {duration_s:.3f}",
        f"model: {model}",
        f"query: {original_query!r}",
        f"token_usage: {json.dumps(token_ledger.to_dict(), indent=2)}",
        "",
        "=== trace steps (state snapshots after each graph tick / values mode) ===",
    ]
    for i, step in enumerate(trace_steps):
        log_lines.append(
            f"--- step {i} t={step.get('elapsed_s', 0):.3f}s @ {step.get('timestamp', '')} ---"
        )
        st = step.get("state")
        if st is not None:
            log_lines.append(json.dumps(st, indent=2, default=str)[:20000])
        else:
            log_lines.append(json.dumps(step, indent=2, default=str)[:20000])
        log_lines.append("")

    trace_log_path = run_dir / "trace.log"
    trace_log_path.write_text("\n".join(log_lines), encoding="utf-8")

    out_paths: dict[str, str] = {
        "summary_md": str(summary_path),
        "trace_json": str(trace_json_path),
        "trace_log": str(trace_log_path),
        "run_dir": str(run_dir),
    }
    for key, name in (("plan_json", "plan.json"), ("plan_md", "plan.md"), ("run_status", "run_status.json")):
        p = run_dir / name
        if p.is_file():
            out_paths[key] = str(p)
    return out_paths


def run_dir_for_run_id(root: Path, run_id: str) -> Path:
    """One folder per run, keyed by full run_id (modular, self-contained)."""
    return (root / run_id).resolve()


def default_run_dir(root: Path, run_id: str) -> Path:
    """All artifacts for a run: `<root>/<run_id>/` (timestamps only in file contents)."""
    return run_dir_for_run_id(root, run_id)


def format_plan_for_display(state: dict[str, Any]) -> str:
    """CLI-friendly text after supervisor; does not include secrets."""
    lines: list[str] = [
        "",
        "========== SUPERVISOR PLAN ==========",
        f"Run ID: {state.get('run_id', '')}",
        f"Model:  {state.get('model', '')}",
        f"Objective: {state.get('main_objective', '')}",
        f"Context:   {state.get('context', '')}",
        "",
        "Tasks (order matters):",
    ]
    for i, t in enumerate(state.get("tasks") or [], 1):
        lines.append(f"  {i}. [{t.get('task_id', '')}] {t.get('tool_name', '')}")
        p = t.get("params")
        lines.append(f"      params: {json.dumps(p, default=str) if p is not None else '{}'}")
        c = (t.get("context") or "").strip()
        if c:
            lines.append(f"      note:   {c[:300]}")
    lines.append("======================================")
    lines.append("")
    return "\n".join(lines)


def write_plan_files(
    run_dir: Path,
    state: dict[str, Any],
    *,
    approved: bool | None = None,
    md_preamble: str = "",
) -> dict[str, str]:
    """Write plan.json and plan.md; `approved` None = submitted, awaiting confirmation."""
    run_dir.mkdir(parents=True, exist_ok=True)
    tasks_out = []
    for t in state.get("tasks") or []:
        if not isinstance(t, dict):
            continue
        tasks_out.append(
            {
                "task_id": t.get("task_id"),
                "plan_id": t.get("plan_id"),
                "tool_name": t.get("tool_name"),
                "params": t.get("params"),
                "context": t.get("context"),
            }
        )
    plan = {
        "run_id": state.get("run_id"),
        "model": state.get("model"),
        "original_query": state.get("original_query"),
        "main_objective": state.get("main_objective"),
        "context": state.get("context"),
        "tasks": tasks_out,
        "approved": approved,
    }
    if approved is True:
        plan["approved_at"] = datetime.now(timezone.utc).isoformat()
    elif approved is False:
        plan["rejected_at"] = datetime.now(timezone.utc).isoformat()
    pj = run_dir / "plan.json"
    pj.write_text(json.dumps(plan, indent=2, default=str) + "\n", encoding="utf-8")
    # Human-readable mirror
    pm = run_dir / "plan.md"
    md_lines = [
        f"# Plan — {plan.get('run_id')}",
        "",
        f"- **Model:** {plan.get('model')}",
        f"- **Approved:** {plan.get('approved')}",
        f"- **Objective:** {plan.get('main_objective', '')}",
        f"- **Context:** {plan.get('context', '')}",
        "",
        "| Step | task_id | tool | params (summary) |",
        "| --- | --- | --- | --- |",
    ]
    for i, t in enumerate(tasks_out, 1):
        pstr = json.dumps(t.get("params"), default=str)[:120]
        md_lines.append(
            f"| {i} | `{t.get('task_id', '')}` | `{t.get('tool_name', '')}` | `{pstr}` |"
        )
    body = "\n".join(md_lines) + "\n"
    if md_preamble:
        body = md_preamble.rstrip() + "\n\n---\n\n" + body
    pm.write_text(body, encoding="utf-8")
    return {"plan_json": str(pj), "plan_md": str(pm)}


def write_run_status(run_dir: Path, status: str, **extra: Any) -> str:
    run_dir.mkdir(parents=True, exist_ok=True)
    p = {
        "status": status,
        "at": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    path = run_dir / "run_status.json"
    path.write_text(json.dumps(p, indent=2) + "\n", encoding="utf-8")
    return str(path)
