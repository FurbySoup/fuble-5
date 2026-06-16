#!/usr/bin/env python3
"""Aggregate filled rubric score files into results/REPORT.md.

3-arm design (baseline / trimmed / full). Computes, per model:
  - per-cell mean total and per-criterion means (averaged over tasks x repeats)
  - a noise floor = typical run-to-run std of the total across repeats (same model/cond/task)
  - within-model deltas vs baseline, flagged as "within noise" when |delta| <= noise floor
  - the bulk effect (full - trimmed): what the ~28.7k-token bulk added beyond the guidance
Also folds in raw-output metadata (latency, tokens, truncation) for a cost/health summary.

Usage:
    python score_report.py                 # uses ../results
"""
from __future__ import annotations

import argparse
import statistics as stats
import sys
from collections import defaultdict
from pathlib import Path

import yaml

# Windows consoles default to cp1252 and choke on ±/×/− in the preview print.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CRITERIA = ["correctness", "completeness", "code_quality", "instruction_follow",
            "conciseness", "safety_calibration", "tool_discipline"]
MAX_TOTAL = len(CRITERIA) * 5
CONDITIONS = ["baseline", "trimmed", "full"]   # baseline is the reference
BASELINE = "baseline"


def load_yaml(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def parse_front_matter(text: str) -> dict:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return yaml.safe_load(text[3:end]) or {}
    return {}


def crit(row, c):
    e = (row.get("scores") or {}).get(c)
    return (e.get("value") if isinstance(e, dict) else e) if e is not None else None


def total_of(row):
    vals = [crit(row, c) for c in CRITERIA]
    return sum(v for v in vals if v is not None)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return stats.fmean(xs) if xs else None


def fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def signed(x, nd=2):
    if x is None:
        return "n/a"
    return ("+" if x >= 0 else "") + f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    args = ap.parse_args()
    results_dir = Path(args.results).resolve()

    rows = []
    for p in sorted((results_dir / "scores").glob("*.yaml")):
        if p.name.startswith("_"):
            continue
        d = load_yaml(p)
        if d:
            d["_stem"] = p.stem
            rows.append(d)
    if not rows:
        raise SystemExit(f"No score files in {results_dir/'scores'}. Run judge.py first.")

    models = sorted({r["model"] for r in rows})

    # Index: cell[(model,cond)] -> rows ; by_task[(model,cond,task)] -> rows (across repeats)
    cell = defaultdict(list)
    by_task = defaultdict(list)
    for r in rows:
        cell[(r["model"], r["prompt"])].append(r)
        by_task[(r["model"], r["prompt"], r["task_id"])].append(r)

    # Noise floor per model: mean over (cond,task) of std-of-total across repeats.
    noise = {}
    for m in models:
        stds = []
        for (mm, cond, tid), rs in by_task.items():
            if mm != m:
                continue
            totals = [total_of(r) for r in rs]
            if len(totals) >= 2:
                stds.append(stats.pstdev(totals))
        noise[m] = mean(stds)

    def cell_total_mean(m, cond):
        rs = cell.get((m, cond))
        return mean([total_of(r) for r in rs]) if rs else None

    def cell_crit_mean(m, cond, c):
        rs = cell.get((m, cond))
        return mean([crit(r, c) for r in rs]) if rs else None

    L = ["# Fable 5 A/B Experiment — Score Report", ""]
    L.append(f"Scored outputs: **{len(rows)}**. Models: {', '.join(models)}. "
             f"Conditions: {', '.join(CONDITIONS)}. Max/output: **{MAX_TOTAL}**.")
    L.append("")
    L.append("> **Reading this:** the headline is each model's **within-model delta** vs its "
             "baseline. `trimmed−baseline` isolates the Fable-5 coding guidance; `full−baseline` "
             "is the whole verbatim prompt; `full−trimmed` is the effect of the ~28.7k-token bulk. "
             "A delta at or below the model's **noise floor** (run-to-run std) is *not* "
             "distinguishable from sampling noise — treat it as null.")
    L.append("")

    # ---- Headline totals ----
    L.append("## Headline: total score per cell (mean over tasks × repeats, /35)")
    L.append("")
    L.append("| Model | noise floor | baseline | trimmed | full | Δ trimmed | Δ full | Δ bulk (full−trimmed) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for m in models:
        base = cell_total_mean(m, "baseline")
        trim = cell_total_mean(m, "trimmed")
        full = cell_total_mean(m, "full")
        d_trim = (trim - base) if (trim is not None and base is not None) else None
        d_full = (full - base) if (full is not None and base is not None) else None
        d_bulk = (full - trim) if (full is not None and trim is not None) else None
        nf = noise[m]

        def annot(d):
            if d is None:
                return "n/a"
            tag = signed(d)
            if nf is not None and abs(d) <= nf:
                tag += " ⚠noise"
            return tag
        L.append(f"| {m} | ±{fmt(nf)} | {fmt(base)} | {fmt(trim)} | {fmt(full)} | "
                 f"{annot(d_trim)} | {annot(d_full)} | {annot(d_bulk)} |")
    L.append("")
    L.append("`⚠noise` = magnitude within the run-to-run noise floor; not a real effect at this sample size.")
    L.append("")

    # ---- Per-criterion deltas ----
    L.append("## Per-criterion means and deltas vs baseline")
    for m in models:
        L.append("")
        L.append(f"### {m}")
        L.append("")
        L.append("| Criterion | baseline | trimmed | full | Δ trimmed | Δ full |")
        L.append("|---|---|---|---|---|---|")
        for c in CRITERIA:
            b = cell_crit_mean(m, "baseline", c)
            t = cell_crit_mean(m, "trimmed", c)
            f = cell_crit_mean(m, "full", c)
            dt = (t - b) if (t is not None and b is not None) else None
            df = (f - b) if (f is not None and b is not None) else None
            L.append(f"| {c} | {fmt(b)} | {fmt(t)} | {fmt(f)} | {signed(dt)} | {signed(df)} |")
    L.append("")

    # ---- Health / cost from raw metadata ----
    raw_meta = {}
    for p in sorted((results_dir / "raw_outputs").glob("*.md")):
        raw_meta[p.stem] = parse_front_matter(p.read_text(encoding="utf-8"))
    L.append("## Run health & cost (from raw-output metadata)")
    L.append("")
    L.append("| Model | cond | n | avg latency s | avg prompt tok | avg completion tok | truncated |")
    L.append("|---|---|---|---|---|---|---|")
    health = defaultdict(lambda: {"lat": [], "ptok": [], "ctok": [], "trunc": 0, "n": 0})
    for stem, meta in raw_meta.items():
        key = (meta.get("model"), meta.get("prompt_condition"))
        h = health[key]
        h["n"] += 1
        if meta.get("latency_s") is not None:
            h["lat"].append(meta["latency_s"])
        u = meta.get("usage") or {}
        if u.get("prompt_tokens"):
            h["ptok"].append(u["prompt_tokens"])
        if u.get("completion_tokens"):
            h["ctok"].append(u["completion_tokens"])
        if meta.get("truncated"):
            h["trunc"] += 1
    for (m, cond) in sorted(health):
        h = health[(m, cond)]
        L.append(f"| {m} | {cond} | {h['n']} | {fmt(mean(h['lat']),1)} | "
                 f"{fmt(mean(h['ptok']),0)} | {fmt(mean(h['ctok']),0)} | {h['trunc']} |")
    L.append("")

    # ---- Flags ----
    L.append("## Flags")
    flagged = [(r["_stem"], r.get("flags")) for r in rows if r.get("flags")]
    if flagged:
        for stem, flags in flagged:
            L.append(f"- `{stem}`: {', '.join(flags)}")
    else:
        L.append("- none recorded")
    L.append("")

    # ---- Caveats ----
    judge_models = sorted({r.get("scorer", "") for r in rows})
    L.append("## Caveats (read before quoting any number)")
    L.append(f"- **Scorer:** {', '.join(judge_models)} — an independent frontier model with no "
             "vendor overlap with either candidate (Qwen/Moonshot), judging blind (model/condition "
             "labels stripped and shuffled). Residual risk: an LLM judge may still subtly favor "
             "outputs resembling its own style, and `full`-condition answers can contain "
             "self-references that partially leak blinding.")
    L.append("- **Sample size is small** — the noise-floor flag is a heuristic, not a significance test.")
    L.append("- **Kimi runs at forced temperature=1** (high variance); its deltas are inherently "
             "less reliable than qwen's at temp=0.2, regardless of repeats.")
    L.append("- **Cross-model comparisons are descriptive only** (different models, temperatures, "
             "token budgets). The defensible results are the within-model deltas.")
    L.append("- **Ceiling effects:** trivial tasks may score 5 across the board and carry no signal; "
             "weight the discriminating tasks (rate-limiter, refactor, tool-probe) when interpreting.")
    L.append("")

    out = results_dir / "REPORT.md"
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {out}\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
