# Findings — Fable 5 System-Prompt A/B Experiment

*168 generations (2 models × 3 conditions × 7 coding tasks; qwen ×3, Kimi ×5 repeats).
Correctness checked objectively by executed tests; remaining criteria scored by a blinded,
vendor-neutral Claude judge. Full numbers in `results/REPORT.md` (regenerable).*

## Headline (total /35, mean over tasks × repeats)

| Model | baseline | trimmed (guidance) | full (verbatim) | Δ trimmed | Δ full | noise floor |
|---|---|---|---|---|---|---|
| **kimi-k2.7-code** | 34.06 | 34.83 | 31.26 | +0.77 *(noise)* | **−2.80** | ±1.43 |
| **qwen3-coder:30b** | 33.43 | 33.19 | 24.95 | −0.24 *(noise)* | **−8.48** | ±0.74 |

## What we can defensibly conclude

1. **The Fable 5 *behavioral guidance* (trimmed arm) does essentially nothing to coding quality.**
   For both models, `trimmed − baseline` falls **within the run-to-run noise floor** (+0.77 for
   Kimi, −0.24 for qwen) — indistinguishable from zero. The tone/formatting/conciseness/refusal
   guidance neither meaningfully helped nor hurt on these tasks.

2. **The *verbatim* Fable 5 prompt (full arm) significantly hurts — and the damage is the bulk,
   not the guidance.** `full − trimmed` ≈ `full − baseline` for both models, so the ~28.7k-token
   bulk (tool definitions, memory/artifact/skills/filesystem scaffolding, policy text) is what
   causes the drop, not the coding advice. Both `full` deltas comfortably exceed each model's
   noise floor, so these are real effects, not sampling noise.

3. **The smaller local model is far more fragile to the irrelevant bulk than the frontier model.**
   qwen's `full` collapse (−8.48) is broad — every criterion drops ~1.0–1.5, including
   correctness (−1.48). Kimi's `full` drop (−2.80) is milder and shallower (~−0.3 to −0.6 per
   criterion). Loading 29k tokens of off-task instructions degraded the 30B model's attention and
   instruction-following across the board; the frontier model mostly shrugged it off.

4. **The predicted failure mode is confirmed and localized.** Phantom tool calls (`web_search`,
   `bash_tool`, `create_file`) appeared almost exclusively in the `full` condition, concentrated
   on the tool-tempting tasks (`tool-probe`, `sql-query`) — see the flags in `results/REPORT.md`.
   Because correctness is scored on the *code itself* (extracted even from phantom tool blocks),
   this shows up sharply in `tool_discipline` (qwen −1.29, Kimi −0.34) and in the
   tool-dependent tasks, rather than being smeared across correctness.

## What this does NOT show

- **Not** that Claude's prompt engineering is "bad" — the *adapted* guidance (trimmed) was
  harmless; the harm came from grafting capability scaffolding the models can't honor.
- **No clean cross-model claim.** Different models, different temperatures (Kimi forced to
  temp=1), different token budgets. The defensible results are the within-model deltas above.
- Kimi's numbers carry less confidence (forced temp=1 → noise floor ±1.43, ~2× qwen's).

## Practical takeaway

You cannot improve (or even safely transfer) a non-Anthropic coding model by pasting Claude's
verbatim system prompt onto it — it ranges from neutral to actively harmful, worse for smaller
models, driven by capability/tool scaffolding the model can't satisfy. If you want any of Fable
5's behavioral style, port **only** the relevant guidance (the trimmed arm) — and even then,
expect no measurable coding-quality gain on tasks like these.

## Method notes / cost

- Judge = Claude, **blind** (labels stripped, shuffled), zero vendor overlap with either
  candidate. Objective correctness via executed tests overrides the judge where available.
- Critical setup fix: stock Ollama silently truncated the 28.7k-token prompt to 4k; a
  high-context model variant (`num_ctx 40960`) was required for qwen to actually see the `full`
  prompt (verified ~29.2k prompt tokens).
- Estimated Moonshot spend ≈ **$1.2** (from logged tokens; context caching likely reduced it).
  No judge API cost — Claude judged within-session. Comfortably within the £20 credit.
