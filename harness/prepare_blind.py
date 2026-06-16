#!/usr/bin/env python3
"""Prepare a BLIND judging set so the judge (Claude, this session) scores without knowing
which model or system-prompt condition produced each output — removing self-preference and
condition-expectation bias.

For every raw output it writes results/blind/{anon_id}.md containing ONLY the task spec and
the candidate's answer (no model, no condition, no repeat index), in shuffled order. The
secret mapping anon_id -> real identity is written to results/blind/_map.json (consumed later
by deblind_merge.py; the judge must not read it).

Usage:
    python prepare_blind.py                 # uses ../results, ../tasks/tasks.yaml
    python prepare_blind.py --seed 7
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import yaml


def parse_front_matter(text: str):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return yaml.safe_load(text[3:end]) or {}, text[end + 4:].lstrip("\n")
    return {}, text


def case_markdown(task: dict, answer: str) -> str:
    constraints = "\n".join(f"  - {c}" for c in task.get("constraints", [])) or "  (none stated)"
    checklist = "\n".join(f"  - {c}" for c in task.get("checklist", [])) or "  (none stated)"
    return f"""# Blind judging case

## Task that was given to an anonymous AI
{task['prompt'].strip()}

### Explicit constraints
{constraints}

### Completeness checklist
{checklist}

## The AI's answer (verbatim)
{answer.strip()}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    ap.add_argument("--tasks", default="../tasks/tasks.yaml")
    ap.add_argument("--seed", type=int, default=1, help="shuffle seed (reproducible)")
    args = ap.parse_args()

    results_dir = Path(args.results).resolve()
    raw_dir = results_dir / "raw_outputs"
    blind_dir = results_dir / "blind"
    blind_dir.mkdir(parents=True, exist_ok=True)
    # clear any stale blind set
    for old in blind_dir.glob("*"):
        old.unlink()

    tasks = {t["id"]: t for t in yaml.safe_load(
        Path(args.tasks).resolve().read_text(encoding="utf-8"))["tasks"]}

    items = []
    for md in sorted(raw_dir.glob("*.md")):
        meta, body = parse_front_matter(md.read_text(encoding="utf-8"))
        tid = meta.get("task_id")
        if tid not in tasks:
            continue
        items.append((md.stem, meta, body, tasks[tid]))

    if not items:
        raise SystemExit(f"No raw outputs in {raw_dir}. Run run_experiment.py first.")

    rng = random.Random(args.seed)
    rng.shuffle(items)

    mapping = {}
    width = max(3, len(str(len(items))))
    for i, (stem, meta, body, task) in enumerate(items, 1):
        anon_id = f"c{i:0{width}d}"
        (blind_dir / f"{anon_id}.md").write_text(case_markdown(task, body), encoding="utf-8")
        mapping[anon_id] = {
            "tag": stem,
            "task_id": meta.get("task_id"),
            "model": meta.get("model"),
            "prompt": meta.get("prompt_condition"),
            "repeat": meta.get("repeat"),
            "truncated": bool(meta.get("truncated")),
        }

    (blind_dir / "_map.json").write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} blind cases to {blind_dir} (seed={args.seed}).")
    print("Judge results/blind/c*.md WITHOUT reading _map.json, then record verdicts in")
    print("results/blind/verdicts.yaml and run deblind_merge.py.")


if __name__ == "__main__":
    main()
