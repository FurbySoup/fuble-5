#!/usr/bin/env python3
"""Run the Fable 5 A/B coding experiment: iterate the 2x2 (model x system-prompt) over
every task and save each raw model response with metadata.

Usage:
    python run_experiment.py --config config.yaml
    python run_experiment.py --config config.yaml --only qwen3-coder --prompt fable5
    python run_experiment.py --config config.yaml --repeats 3
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import yaml
from openai import OpenAI


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def build_client(model_cfg: dict) -> OpenAI:
    api_key = os.environ.get(model_cfg["api_key_env"]) or model_cfg.get("default_api_key")
    if not api_key:
        raise SystemExit(
            f"Missing API key: set ${model_cfg['api_key_env']} for model '{model_cfg['key']}'"
        )
    return OpenAI(base_url=model_cfg["base_url"], api_key=api_key)


def call_model(client: OpenAI, model_cfg: dict, system_prompt: str, user_prompt: str,
               decoding: dict) -> dict:
    """Single chat completion. Returns dict with content, latency, usage, raw params."""
    t0 = time.time()
    kwargs = dict(
        model=model_cfg["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=decoding["temperature"],
        top_p=decoding["top_p"],
        max_tokens=decoding["max_tokens"],
    )
    # seed is best-effort; some providers reject the field.
    try:
        resp = client.chat.completions.create(seed=decoding.get("seed"), **kwargs)
    except TypeError:
        resp = client.chat.completions.create(**kwargs)
    latency = time.time() - t0

    usage = getattr(resp, "usage", None)
    return {
        "content": resp.choices[0].message.content or "",
        "latency_s": round(latency, 2),
        "finish_reason": resp.choices[0].finish_reason,
        "usage": {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
        } if usage else None,
    }


def front_matter(meta: dict) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False).strip() + "\n---\n\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--only", help="run only this model key")
    ap.add_argument("--prompt", choices=["baseline", "fable5"], help="run only this condition")
    ap.add_argument("--repeats", type=int, help="override repeats from config")
    args = ap.parse_args()

    cfg_path = Path(args.config).resolve()
    root = cfg_path.parent
    cfg = load_yaml(cfg_path)

    decoding = cfg["decoding"]
    repeats = args.repeats or cfg.get("repeats", 1)
    prompts = {k: read_text((root / v).resolve()) for k, v in cfg["prompts"].items()}
    tasks = load_yaml((root / cfg["tasks_file"]).resolve())["tasks"]
    out_dir = (root / cfg["output_dir"]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    models = cfg["models"]
    if args.only:
        models = [m for m in models if m["key"] == args.only]
        if not models:
            raise SystemExit(f"No model with key '{args.only}'")
    prompt_keys = [args.prompt] if args.prompt else list(prompts.keys())

    total = len(models) * len(prompt_keys) * len(tasks) * repeats
    done = 0
    print(f"Running {total} generations "
          f"({len(models)} models x {len(prompt_keys)} prompts x {len(tasks)} tasks x {repeats} repeats)\n")

    for model_cfg in models:
        client = build_client(model_cfg)
        for pkey in prompt_keys:
            for task in tasks:
                for rep in range(1, repeats + 1):
                    done += 1
                    rep_suffix = f"__r{rep}" if repeats > 1 else ""
                    tag = f"{model_cfg['key']}__{pkey}__{task['id']}{rep_suffix}"
                    print(f"[{done}/{total}] {tag} ...", end=" ", flush=True)
                    try:
                        result = call_model(client, model_cfg, prompts[pkey],
                                            task["prompt"], decoding)
                    except Exception as e:  # noqa: BLE001 — log and continue the battery
                        print(f"ERROR: {e}")
                        result = {"content": f"[GENERATION ERROR] {e}", "latency_s": None,
                                  "finish_reason": "error", "usage": None}

                    meta = {
                        "tag": tag,
                        "model_key": model_cfg["key"],
                        "model": model_cfg["model"],
                        "prompt_condition": pkey,
                        "task_id": task["id"],
                        "category": task.get("category"),
                        "tool_dependent": task.get("tool_dependent", False),
                        "repeat": rep,
                        "decoding": decoding,
                        "latency_s": result["latency_s"],
                        "finish_reason": result["finish_reason"],
                        "usage": result["usage"],
                    }
                    out_path = out_dir / f"{tag}.md"
                    out_path.write_text(front_matter(meta) + result["content"], encoding="utf-8")
                    print(f"ok ({result['latency_s']}s)" if result["finish_reason"] != "error" else "saved error")

    print(f"\nDone. Raw outputs in: {out_dir}")
    print("Next: score each output per rubric/AB_TESTING_RUBRIC.md into results/scores/, "
          "then run score_report.py")


if __name__ == "__main__":
    main()
