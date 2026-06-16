# fuble-5 — Fable 5 System Prompt A/B Experiment

An experiment to measure how Anthropic's **Claude Fable 5 system prompt** affects the
coding performance of two non-Anthropic models when it is grafted onto them:

| Candidate | What it is | How it's served |
|-----------|-----------|-----------------|
| **Local: `qwen3-coder:30b`** | Qwen3-Coder-30B-A3B (MoE, ~3B active), Q4, 18 GB | Ollama (OpenAI-compatible API) |
| **Remote: `kimi-k2.7-code`** | Moonshot AI frontier coding model | Moonshot OpenAI-compatible API |

The core question: **does giving a non-Claude model Claude's Fable 5 system prompt change
how well it does coding tasks, and in which direction — and is any change due to the
*guidance* or just the 28.7k-token *bulk* of the prompt?**

## The design (2 models × 3 prompt conditions)

For each model we run the same coding task battery under three system-prompt conditions:

| Condition | File | Purpose |
|-----------|------|---------|
| **baseline** | `system-prompts/baseline.md` | Neutral minimal coding prompt — the control / "before" |
| **trimmed** | `system-prompts/fable-5-trimmed.md` | Only Fable 5's coding-relevant behavioral guidance — isolates *the guidance* |
| **full** | `system-prompts/fable-5-full.md` | The verbatim ~28.7k-token Fable 5 prompt — *guidance + bulk* |

The three headline within-model deltas:
- `trimmed − baseline` → effect of the behavioral guidance alone
- `full − baseline` → effect of the whole verbatim prompt ("before vs after Fable 5")
- `full − trimmed` → effect of the ~28.7k-token bulk (tool defs, policy, context dilution)

This 3-arm design is what lets us **attribute cause**, not just observe that something changed.

Each output is scored with the rubric in `rubric/AB_TESTING_RUBRIC.md` (7 criteria, /35).
Correctness is checked **objectively** (executed tests) where possible; the rest is scored by
a **blinded LLM-judge**. Each cell is run with **repeats** so we can estimate the run-to-run
noise floor and tell real deltas from sampling noise.

See `EXPERIMENT_DESIGN.md` for full methodology, hypotheses, and threats to validity.

## Hardware

- 64 GB RAM · AMD Ryzen 7 5800X (8c) · NVIDIA RTX 4060 Ti **8 GB**
- The 30B MoE exceeds 8 GB VRAM; Ollama offloads layers to system RAM. Usable but
  not GPU-resident. Token throughput is **not** a scored metric (hardware-confounded),
  but latency is logged for context.

## Layout

```
system-prompts/   baseline.md, fable-5-trimmed.md, fable-5-full.md (3 conditions)
rubric/           AB_TESTING_RUBRIC.md (the scoring instrument)
tasks/            tasks.yaml (the coding battery, frozen)
harness/
  run_experiment.py   generate: 2 models × 3 conditions × tasks × repeats -> raw_outputs/
  autocheck.py        objective correctness: execute test cases -> autocheck/
  judge.py            blinded LLM-judge for subjective criteria -> scores/
  score_report.py     aggregate -> REPORT.md (deltas, noise floor, cost)
  config.yaml         models, endpoints, decoding, repeats, judge
results/          raw_outputs/ + autocheck/ + scores/ + REPORT.md
```

## Quick start

```powershell
# 1. Ollama running with the model present
ollama list                       # expect qwen3-coder:30b

# 2. Kimi key in harness/.env (gitignored) — already configured:
#    MOONSHOT_API_KEY=sk-...

# 3. Deps
cd harness
pip install -r requirements.txt

# 4. Pipeline: generate -> autocheck -> judge -> report
python run_experiment.py --config config.yaml     # all cells (use --task X for a smoke test)
python autocheck.py                                # objective correctness on testable tasks
python judge.py --config config.yaml               # blinded LLM-judge scores the rest
python score_report.py                             # -> results/REPORT.md
```

## Important caveats baked into the analysis (also surfaced in REPORT.md)

- **The full Fable 5 prompt references Anthropic-only tools** (`web_search`, `bash_tool`,
  artifacts, MCP, memory) the candidates lack. Their reaction is measured by the rubric's
  `tool_discipline` criterion — it's a finding, not a bug.
- **Kimi is forced to `temperature=1`** by its API (qwen runs at 0.2), so Kimi's deltas are
  inherently noisier; we use more repeats for it and still report less confidence.
- **The LLM-judge shares a vendor with one candidate** (only Moonshot + Ollama are available),
  a self-preference risk; a blinded human spot-check sample is flagged for validation.
- **Cross-model comparison is descriptive only.** The defensible results are within-model deltas.
