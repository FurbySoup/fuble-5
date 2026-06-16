# Experiment Design

## 1. Question & hypotheses

**Research question:** When a non-Anthropic model is given Claude's Fable 5 system prompt,
does its coding performance change relative to its own baseline prompt — and is any change
caused by the *behavioral guidance* or by the *28.7k-token bulk* of the verbatim prompt?

- **H1 (effect exists):** At least one model shows a within-model rubric-score change beyond
  its run-to-run noise floor under some Fable-5 condition.
- **H0 (null):** No within-model delta exceeds the noise floor.
- **H2 (attribution):** The `trimmed` arm (guidance only) and the `full` arm (guidance + bulk)
  separate the cause. If `trimmed−baseline` ≈ `full−baseline`, the guidance drives the effect;
  if they differ, the bulk (length, irrelevant tool/policy text, attention dilution) matters.
- **H3 (directional, exploratory):** Fable 5's verbosity/formatting and refusal guidance
  improve conciseness and instruction-following but may hurt `tool_discipline` when the verbatim
  prompt's tool references induce phantom tool calls in a tool-less candidate.

This is a **pilot with variance estimation**, not a powered statistical test. Deltas are
compared against an empirical noise floor; treat sub-noise deltas as null.

## 2. Factors

| Factor | Levels |
|--------|--------|
| Model | `qwen3-coder:30b` (local, temp 0.2), `kimi-k2.7-code` (remote, forced temp 1) |
| System prompt | `baseline`, `trimmed`, `full` |

Fully crossed → 6 cells. Each cell is repeated (qwen ×3, kimi ×5) to estimate variance.

## 3. Controlled variables

- **Task set** — identical tasks, identical order (`tasks/tasks.yaml`), frozen.
- **Decoding** — pinned in `harness/config.yaml`, held **identical across a model's three
  conditions** so within-model deltas are attributable to the prompt. Kimi's API forbids
  `temperature≠1` and `top_p≠0.95`, so it uses a per-model override (applied to all three of
  its conditions equally — the comparison stays clean; only cross-model parity is sacrificed).
- **Scoring instrument** — same rubric, same autocheck, same judge model for every cell.
- **max_tokens = 4096** — raised so the verbose `full` condition isn't silently truncated;
  `finish_reason=='length'` is flagged `truncated` and surfaced in the report.

Deliberately not controlled: throughput/latency (hardware/API-bound) — logged, not scored.

## 4. Procedure (pipeline)

1. **Pre-registration / freeze.** Before runs: task set, rubric, decoding, repeats, and all
   three prompt files are committed and not edited after scoring starts.
2. **Generate** — `run_experiment.py` → `results/raw_outputs/{model}__{cond}__{task}__rN.md`,
   each with metadata (effective decoding, latency, token usage, truncation).
3. **Autocheck** — `autocheck.py` executes the `tests` cases for testable tasks in an isolated
   subprocess → objective correctness (0–5) in `results/autocheck/`. This is the only fully
   objective criterion and overrides the judge's correctness where available.
4. **Blinded judge** — `judge.py` sends the judge model only the task spec + the candidate
   answer (no model/condition labels) and gets 0–5 scores + justifications for the remaining
   criteria → `results/scores/`. A deterministic `spot_check_fraction` is flagged for blinded
   human re-scoring (`_spot_check_queue.txt`) to validate the judge.
5. **Aggregate** — `score_report.py` → `results/REPORT.md`: per-cell means, per-criterion
   deltas, the three within-model deltas, the noise floor and which deltas exceed it, plus a
   cost/health table (latency, tokens, truncations) and the standing caveats.

## 5. "Before and after" framing

- **Before** = `baseline` cell. **After (guidance)** = `trimmed`. **After (verbatim)** = `full`.
- Reported result per model = `trimmed−baseline`, `full−baseline`, and the bulk effect
  `full−trimmed`, each per-criterion and in total, with the noise-floor annotation.

## 6. Threats to validity

| Threat | Mitigation |
|--------|-----------|
| **Tool mismatch.** Full prompt assumes Anthropic tools the candidates lack. | The `trimmed` arm strips tool references; `tool_discipline` criterion measures the reaction; phantom-tool flags recorded. |
| **Prompt length / dilution.** Full prompt is ~28.7k tokens. | The `trimmed` vs `full` contrast isolates the bulk's effect. Prompt tokens logged per cell. |
| **Single-sample noise.** | Repeats per cell → empirical noise floor; sub-noise deltas treated as null. Kimi gets more repeats (forced temp 1). |
| **Scorer subjectivity & bias.** | Objective autocheck for correctness; blinded LLM-judge for the rest; blinded human spot-check sample. |
| **Judge vendor self-preference.** Only Moonshot+Ollama available, so the judge shares a vendor with one candidate. | Disclosed in REPORT; spot-check validates; a third-party judge key can be dropped into `config.judge`. |
| **Ceiling effects.** Trivial tasks score 5 everywhere → no signal. | Battery includes discriminating tasks (rate-limiter, refactor, tool-probe); report weights these. |
| **Determinism.** Kimi ignores seed at temp 1. | Logged; reproducibility claimed only for qwen. |
| **Baseline ≠ true default.** `baseline.md` says "be concise". | Stated explicitly: this is prompt-vs-prompt, not "no prompt vs Fable 5". |

## 7. What we will and won't be able to claim

- **Defensible:** per-model direction and magnitude of change (vs baseline) on this battery,
  with correctness objectively verified, deltas judged against a noise floor, and the
  guidance-vs-bulk attribution from the 3-arm contrast.
- **Weaker for Kimi:** forced temp=1 means higher variance and lower confidence even with repeats.
- **Not claimable:** that Claude's prompt engineering is "good/bad" in general (2 models, small
  battery), or any clean cross-model ranking (different models/temperatures/token budgets).

## 8. Deliverables

`results/raw_outputs/` (responses + metadata), `results/autocheck/` (objective correctness),
`results/scores/` (per-output rubric), `results/REPORT.md` (the synthesized result).
