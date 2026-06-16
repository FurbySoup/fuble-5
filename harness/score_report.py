#!/usr/bin/env python3
"""Aggregate filled rubric score files into results/REPORT.md.

Reads every results/scores/*.yaml (format defined at the bottom of
rubric/AB_TESTING_RUBRIC.md), computes per-cell means, within-model deltas
(After - Before), and a per-criterion breakdown, then writes the report.

Usage:
    python score_report.py                       # uses ../results
    python score_report.py --results ../results
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import yaml

CRITERIA = [
    "correctness", "completeness", "code_quality", "instruction_follow",
    "conciseness", "safety_calibration", "tool_discipline",
]
MAX_TOTAL = len(CRITERIA) * 5
# Map the prompt condition to the experiment's before/after framing.
BEFORE, AFTER = "baseline", "fable5"


def load_scores(scores_dir: Path) -> list[dict]:
    rows = []
    for p in sorted(scores_dir.glob("*.yaml")):
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            continue
        data["_file"] = p.name
        rows.append(data)
    return rows


def crit_value(row: dict, crit: str):
    entry = (row.get("scores") or {}).get(crit)
    if entry is None:
        return None
    return entry["value"] if isinstance(entry, dict) else entry


def mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    args = ap.parse_args()

    results_dir = Path(args.results).resolve()
    rows = load_scores(results_dir / "scores")
    if not rows:
        raise SystemExit(f"No score files in {results_dir/'scores'}. "
                         "Fill them in per the rubric template first.")

    # cell key = (model, prompt_condition)
    cells: dict[tuple, list[dict]] = defaultdict(list)
    models = []
    for r in rows:
        m, p = r["model"], r["prompt"]
        if m not in models:
            models.append(m)
        cells[(m, p)].append(r)

    lines = ["# Fable 5 A/B Experiment — Score Report", ""]
    lines.append(f"Scored outputs: **{len(rows)}** across {len(cells)} cells. "
                 f"Max per output: **{MAX_TOTAL}**.")
    lines.append("")

    # --- Headline 2x2 totals ---
    lines.append("## Headline: total score per cell (mean across tasks)")
    lines.append("")
    lines.append("| Model | Before (baseline) | After (fable5) | Delta (After − Before) |")
    lines.append("|-------|-------------------|----------------|------------------------|")
    for m in models:
        before = mean([sum(crit_value(r, c) or 0 for c in CRITERIA) for r in cells.get((m, BEFORE), [])]) \
            if (m, BEFORE) in cells else None
        after = mean([sum(crit_value(r, c) or 0 for c in CRITERIA) for r in cells.get((m, AFTER), [])]) \
            if (m, AFTER) in cells else None
        delta = (after - before) if (before is not None and after is not None) else None
        sign = "" if delta is None else ("+" if delta >= 0 else "")
        lines.append(f"| {m} | {fmt(before)} /{MAX_TOTAL} | {fmt(after)} /{MAX_TOTAL} | "
                     f"{'n/a' if delta is None else sign + fmt(delta)} |")
    lines.append("")

    # --- Per-criterion breakdown per model ---
    lines.append("## Per-criterion deltas (the interesting story)")
    for m in models:
        lines.append("")
        lines.append(f"### {m}")
        lines.append("")
        lines.append("| Criterion | Before | After | Delta |")
        lines.append("|-----------|--------|-------|-------|")
        for c in CRITERIA:
            b = mean([crit_value(r, c) for r in cells.get((m, BEFORE), [])])
            a = mean([crit_value(r, c) for r in cells.get((m, AFTER), [])])
            d = (a - b) if (a is not None and b is not None) else None
            sign = "" if d is None else ("+" if d >= 0 else "")
            lines.append(f"| {c} | {fmt(b)} | {fmt(a)} | {'n/a' if d is None else sign + fmt(d)} |")
    lines.append("")

    # --- Flags summary ---
    flagged = [(r["_file"], r.get("flags")) for r in rows if r.get("flags")]
    lines.append("## Flags observed")
    if flagged:
        for fname, flags in flagged:
            lines.append(f"- `{fname}`: {', '.join(flags)}")
    else:
        lines.append("- none recorded")
    lines.append("")

    out = results_dir / "REPORT.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print("\n".join(lines[:14]))


if __name__ == "__main__":
    main()
