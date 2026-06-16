#!/usr/bin/env python3
"""De-anonymize the judge's blind verdicts back into per-output score files.

Reads:
  results/blind/_map.json        anon_id -> real identity (model/condition/task/repeat/truncated)
  results/blind/verdicts.yaml    anon_id -> verdict (criterion ints 0-5, optional flags + note)
  results/autocheck/{tag}.yaml   objective correctness (overrides judge where present)

Writes results/scores/{tag}.yaml in the rubric format, with correctness_source recorded.

Verdict entry shape (flexible; ints required, flags/note optional):
  c001:
    correctness: 5
    completeness: 4
    code_quality: 4
    instruction_follow: 5
    conciseness: 3
    safety_calibration: 5
    tool_discipline: 5
    flags: [hallucinated_tool_call]
    note: "one-line justification"

Usage:
    python deblind_merge.py                 # uses ../results
    python deblind_merge.py --scorer "claude-fable-5 (blinded)"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

CRITERIA = ["correctness", "completeness", "code_quality", "instruction_follow",
            "conciseness", "safety_calibration", "tool_discipline"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    ap.add_argument("--scorer", default="claude-fable-5 (blinded)")
    args = ap.parse_args()

    results_dir = Path(args.results).resolve()
    blind_dir = results_dir / "blind"
    autocheck_dir = results_dir / "autocheck"
    scores_dir = results_dir / "scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    mapping = json.loads((blind_dir / "_map.json").read_text(encoding="utf-8"))
    verdicts_path = blind_dir / "verdicts.yaml"
    if not verdicts_path.exists():
        raise SystemExit(f"Missing {verdicts_path}. Judge the blind cases and write verdicts first.")
    verdicts = yaml.safe_load(verdicts_path.read_text(encoding="utf-8")) or {}

    missing = [a for a in mapping if a not in verdicts]
    if missing:
        print(f"WARNING: {len(missing)} cases have no verdict (skipped): {missing[:8]}"
              + (" ..." if len(missing) > 8 else ""))

    written = 0
    for anon_id, ident in mapping.items():
        v = verdicts.get(anon_id)
        if not v:
            continue
        note = str(v.get("note", ""))
        scores = {}
        for c in CRITERIA:
            val = v.get(c)
            scores[c] = {"value": int(val) if val is not None else 0,
                         "note": note if c == "correctness" else ""}
        flags = list(v.get("flags", []) or [])

        # objective correctness overrides the judge where autocheck ran
        tag = ident["tag"]
        correctness_source = "judge"
        ac_path = autocheck_dir / f"{tag}.yaml"
        if ac_path.exists():
            ac = yaml.safe_load(ac_path.read_text(encoding="utf-8"))
            scores["correctness"] = {
                "value": ac["correctness_auto"],
                "note": f"AUTOCHECK {ac['passed']}/{ac['total']} cases"
                        + (f" [{ac['flag']}]" if ac.get("flag") else "")}
            correctness_source = "autocheck"
            if ac.get("flag") in ("exec_error", "no_code_found", "timeout"):
                flags.append("autocheck_" + ac["flag"])
        if ident.get("truncated"):
            flags.append("truncated")

        record = {
            "task_id": ident["task_id"],
            "model": ident["model"],
            "prompt": ident["prompt"],
            "repeat": ident["repeat"],
            "scorer": args.scorer,
            "blind": True,
            "anon_id": anon_id,
            "correctness_source": correctness_source,
            "judge_note": note,
            "scores": scores,
            "total": sum(scores[c]["value"] for c in CRITERIA),
            "flags": sorted(set(flags)),
        }
        (scores_dir / f"{tag}.yaml").write_text(
            yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        written += 1

    print(f"Wrote {written} score files to {scores_dir}. Next: python score_report.py")


if __name__ == "__main__":
    main()
