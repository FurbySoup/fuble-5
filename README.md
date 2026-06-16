# fuble-5 — Fable 5 System Prompt A/B Experiment

An experiment to measure how Anthropic's **Claude Fable 5 system prompt** affects the
coding performance of two non-Anthropic models when it is grafted onto them:

| Candidate | What it is | How it's served |
|-----------|-----------|-----------------|
| **Local: `qwen3-coder:30b`** | Qwen3-Coder-30B-A3B (MoE, ~3B active), Q4, 18 GB | Ollama (OpenAI-compatible API) |
| **Remote: Kimi K2.7 Code** | Moonshot AI frontier coding model | Moonshot OpenAI-compatible API |

The core question: **does giving a non-Claude model Claude's Fable 5 system prompt change
how well it does coding tasks, and in which direction?**

## The design (2 × 2)

For each model we run the same coding task battery under two conditions:

|                    | Baseline system prompt | Fable 5 system prompt |
|--------------------|------------------------|-----------------------|
| `qwen3-coder:30b`  | A1                     | A2                    |
| Kimi K2.7 Code     | B1                     | B2                    |

- **Baseline** = the model's normal/default system prompt (a minimal coding-assistant prompt; see `system-prompts/baseline.md`).
- **Fable 5** = the verbatim extracted Claude Fable 5 prompt (`system-prompts/fable-5-full.md`).

Each cell is scored with the rubric in `rubric/AB_TESTING_RUBRIC.md`. The headline
comparisons are the **within-model deltas** (A2−A1 and B2−B1): does the Fable 5 prompt
help, hurt, or do nothing for each model?

See `EXPERIMENT_DESIGN.md` for the full methodology, hypotheses, and threats to validity.

## Hardware

- 64 GB RAM · AMD Ryzen 7 5800X (8c) · NVIDIA RTX 4060 Ti **8 GB**
- The 30B MoE exceeds 8 GB VRAM; Ollama offloads layers to system RAM. Usable but
  not GPU-resident — expect ~10–20 tok/s. Token throughput is **not** a scored metric
  (it's confounded by hardware), but latency is logged for context.

## Layout

```
system-prompts/   Fable 5 prompt (verbatim) + baseline prompt
rubric/           A/B scoring rubric (the instrument)
tasks/            The coding task battery (tasks.yaml)
harness/          Python runner: executes the 2×2, saves raw outputs
results/          raw_outputs/ (model responses) + scores/ (filled rubrics)
```

## Quick start

```powershell
# 1. Ensure Ollama is running and the model is present
ollama list                       # expect qwen3-coder:30b

# 2. Set the Kimi API key (Moonshot)
$env:MOONSHOT_API_KEY = "sk-..."

# 3. Install harness deps
cd harness
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 4. Run the full 2×2 battery (generates raw outputs)
python run_experiment.py --config config.yaml

# 5. Score the outputs against the rubric (manual or LLM-judge assisted)
#    Fill in results/scores/ from results/raw_outputs/, then:
python score_report.py
```

> **Note on the Fable 5 prompt.** It references Anthropic-internal tools (`web_search`,
> `bash_tool`, artifacts, MCP connectors, memory) that the candidate models won't have.
> That mismatch is part of what we're measuring — see "Threats to validity" in the design doc.
