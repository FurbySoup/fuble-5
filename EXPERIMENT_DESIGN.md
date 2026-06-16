# Experiment Design

## 1. Question & hypotheses

**Research question:** When a non-Anthropic model is given Claude's Fable 5 system prompt,
does its coding performance change relative to its own baseline prompt?

- **H1 (effect exists):** The Fable 5 prompt produces a non-zero change in rubric score
  for at least one model.
- **H0 (null):** No meaningful within-model score difference (|delta| within noise).
- **H2 (directional, exploratory):** Behavioral guidance in the Fable 5 prompt (explicit
  refusal handling, verbosity controls, tool-use discipline, "act when you have enough
  information") *improves* instruction-following and structure but may *hurt* raw task
  completion when it triggers tool references the candidate can't satisfy.

These are exploratory. With a small task battery and one run per cell this is a
**descriptive pilot**, not a powered statistical test. Treat deltas as signal, not proof.

## 2. Factors

| Factor | Levels |
|--------|--------|
| Model | `qwen3-coder:30b` (local), Kimi K2.7 Code (remote) |
| System prompt | Baseline, Fable 5 |

Fully crossed → 4 cells (A1, A2, B1, B2). One block = all 4 cells run on the same task set.

## 3. Controlled variables

Held constant across all four cells:

- **Task set** — identical tasks, identical order (see `tasks/tasks.yaml`).
- **Decoding params** — `temperature`, `top_p`, `max_tokens`, `seed` pinned in
  `harness/config.yaml`. (Seed only fully reproducible on the local model; Kimi may
  ignore it — logged regardless.)
- **Turn budget** — single-turn unless a task is explicitly multi-turn.
- **Scoring instrument** — the same rubric and the same scorer(s) for every cell.

Deliberately **not** controlled (and why): token throughput / wall-clock latency is
hardware- and API-bound, logged for context but excluded from the quality score.

## 4. Procedure

1. **Pre-registration.** Before any runs, freeze: task set, rubric, decoding params,
   and the baseline prompt text. Commit them. No edits to the instrument after scoring starts.
2. **Generation.** `run_experiment.py` iterates all 4 cells × all tasks, saving each raw
   response to `results/raw_outputs/{model}__{prompt}__{task_id}.md` with metadata
   (params, latency, token counts).
3. **Blinding.** `score_report.py --prepare-blind` (optional) strips model/prompt labels
   and shuffles outputs into an anonymized scoring queue to reduce scorer bias.
4. **Scoring.** Each output is scored per `rubric/AB_TESTING_RUBRIC.md`. Code-execution
   criteria (compiles, tests pass) are objective and auto-checked where possible; quality
   criteria are rated by a human and/or an LLM-judge (declare which in the score file).
5. **Analysis.** Compute per-cell totals, then within-model deltas (A2−A1, B2−B1) and the
   cross-model comparison. Report per-criterion breakdowns, not just totals.

## 5. "Before and after" framing

The user's framing — *score each model before and after updating to the Fable 5 prompt* —
maps directly onto the within-model delta:

- **Before** = baseline cell (A1 / B1)
- **After** = Fable 5 cell (A2 / B2)
- **Reported result** = After − Before, per criterion and in total, per model.

## 6. Threats to validity

| Threat | Mitigation |
|--------|-----------|
| **Tool mismatch.** Fable 5 prompt assumes Anthropic tools (web_search, bash_tool, artifacts, MCP, memory) the candidates lack. | Tag tasks that don't need tools as the *core* battery; report tool-dependent tasks separately. Note refusals/hallucinated tool calls as a rubric observation. |
| **Prompt length.** Fable 5 is ~1,800 lines (~30k+ tokens), eating context window and possibly degrading attention. | Log prompt token count; check candidate context limits. Note any truncation. |
| **Scorer bias.** Knowing which cell produced an output biases ratings. | Optional blinding step (§4.3). Use a fixed rubric with concrete anchors. |
| **Single run / small n.** No statistical power. | Frame as a pilot. Optionally run k repeats per cell (`--repeats k`) and report mean ± range. |
| **Judge model bias.** An LLM judge may favor outputs that resemble its own style. | Use a neutral judge model, disclose it, spot-check against human scores. |
| **Seed/determinism.** Remote API may ignore seed. | Log actual params returned; flag non-determinism. |

## 7. Outputs / deliverables

- `results/raw_outputs/` — every model response with metadata.
- `results/scores/` — one filled rubric per output.
- `results/REPORT.md` — generated summary: the 2×2 score table, within-model deltas,
  per-criterion breakdown, and a narrative of observed behavioral changes.
