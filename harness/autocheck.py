#!/usr/bin/env python3
"""Objective correctness check for testable tasks.

For every raw output whose task has a `tests` block (language: python) in tasks.yaml,
extract the code, run the test cases in an isolated subprocess, and record an OBJECTIVE
correctness score (0-5) in results/autocheck/{tag}.yaml. score_report.py merges these over
the judge's subjective correctness so criterion 1 is grounded in execution, not opinion.

Non-testable tasks (no `tests` field, or non-python language) are skipped here and left to
the judge. Outputs whose code errors on run are scored 0 and flagged for human review.

Usage:
    python autocheck.py                 # uses ../results and ../tasks/tasks.yaml
    python autocheck.py --task rev-words
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

FENCE_RE = re.compile(r"```([\w+-]*)\n(.*?)```", re.DOTALL)

RUNNER_TEMPLATE = """\
import json
{code}
# ---- autocheck harness (appended) ----
_CASES = {cases!r}
_RESULTS = []
for _c in _CASES:
    try:
        _actual = eval(_c["call"])
        _expected = eval(_c["expect"])
        _RESULTS.append({{"call": _c["call"], "ok": bool(_actual == _expected),
                          "actual": repr(_actual)}})
    except Exception as _e:
        _RESULTS.append({{"call": _c["call"], "ok": False, "error": repr(_e)}})
print("AUTOCHECK_JSON:" + json.dumps(_RESULTS))
"""


def parse_front_matter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            body = text[end + 4:].lstrip("\n")
            return meta, body
    return {}, text


def extract_python(body: str) -> str:
    """Concatenate python code fences; fall back to unlabeled fences."""
    labeled, unlabeled = [], []
    for lang, code in FENCE_RE.findall(body):
        if lang.lower() in ("python", "py"):
            labeled.append(code)
        elif lang == "":
            unlabeled.append(code)
    blocks = labeled or unlabeled
    return "\n\n".join(blocks).strip()


def run_cases(code: str, cases: list[dict], timeout: int = 15) -> dict:
    if not code:
        return {"correctness_auto": 0, "passed": 0, "total": len(cases),
                "flag": "no_code_found", "detail": "no code block in output"}
    script = RUNNER_TEMPLATE.format(code=code, cases=cases)
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(script)
        path = f.name
    try:
        proc = subprocess.run([sys.executable, path], capture_output=True, text=True,
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"correctness_auto": 0, "passed": 0, "total": len(cases),
                "flag": "timeout", "detail": f"exceeded {timeout}s (possible infinite loop)"}
    finally:
        Path(path).unlink(missing_ok=True)

    marker = "AUTOCHECK_JSON:"
    line = next((l for l in proc.stdout.splitlines() if l.startswith(marker)), None)
    if line is None:
        err = (proc.stderr or proc.stdout).strip().splitlines()
        return {"correctness_auto": 0, "passed": 0, "total": len(cases),
                "flag": "exec_error", "detail": err[-1] if err else "no output / crashed"}

    results = json.loads(line[len(marker):])
    passed = sum(1 for r in results if r["ok"])
    total = len(results)
    # 5 if all pass; otherwise proportional, rounded, but a passing-none scores 0.
    score = 5 if passed == total else round(5 * passed / total) if total else 0
    flag = None if passed == total else "partial_fail"
    return {"correctness_auto": score, "passed": passed, "total": total,
            "flag": flag, "detail": results}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default="../results")
    ap.add_argument("--tasks", default="../tasks/tasks.yaml")
    ap.add_argument("--task", help="limit to one task id")
    args = ap.parse_args()

    results_dir = Path(args.results).resolve()
    raw_dir = results_dir / "raw_outputs"
    out_dir = results_dir / "autocheck"
    out_dir.mkdir(parents=True, exist_ok=True)

    tasks = {t["id"]: t for t in yaml.safe_load(Path(args.tasks).resolve()
                                               .read_text(encoding="utf-8"))["tasks"]}

    checked = skipped = 0
    for md in sorted(raw_dir.glob("*.md")):
        meta, body = parse_front_matter(md.read_text(encoding="utf-8"))
        tid = meta.get("task_id")
        if args.task and tid != args.task:
            continue
        task = tasks.get(tid)
        tests = (task or {}).get("tests")
        if not tests or tests.get("language") != "python":
            skipped += 1
            continue

        outcome = run_cases(extract_python(body), tests["cases"])
        record = {
            "tag": meta.get("tag", md.stem),
            "task_id": tid,
            "model": meta.get("model"),
            "prompt": meta.get("prompt_condition"),
            "repeat": meta.get("repeat"),
            **outcome,
        }
        (out_dir / f"{md.stem}.yaml").write_text(
            yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
        checked += 1
        flag = f" [{outcome['flag']}]" if outcome.get("flag") else ""
        print(f"{md.stem}: correctness_auto={outcome['correctness_auto']} "
              f"({outcome['passed']}/{outcome['total']}){flag}")

    print(f"\nAutochecked {checked}, skipped {skipped} (non-testable). "
          f"Records in {out_dir}")


if __name__ == "__main__":
    main()
