# Starter prompt — Session 2: design & A/B-test an optimized "trimmed" system prompt

Paste everything below the line into a fresh Claude Code session opened in this repo
(`C:\Users\Mark\Desktop\Solo Dev Projects\fuble-5`). It is self-contained.

---

You are continuing the **fuble-5** experiment. Work directory:
`C:\Users\Mark\Desktop\Solo Dev Projects\fuble-5` (git repo, remote `origin` = GitHub
FurbySoup/fuble-5, branch `main`). Read `README.md`, `EXPERIMENT_DESIGN.md`, `FINDINGS.md`,
and `rubric/AB_TESTING_RUBRIC.md` first to orient.

## What already happened (Session 1)

We A/B-tested whether grafting Claude's Fable 5 system prompt onto two non-Anthropic coding
models changes their coding performance. Models: **`kimi-k2.7-code`** (Moonshot API) and
**`qwen3-coder:30b`** (local Ollama). Three prompt conditions: `baseline` (neutral minimal),
`trimmed` (Fable 5's coding-relevant behavioral guidance, tool references stripped), `full`
(verbatim ~28.7k-token prompt). 168 generations, blinded Claude judge, objective correctness
via executed tests. Headline (total /35):

| Model | baseline | trimmed | full | Δtrimmed | Δfull | noise |
|---|---|---|---|---|---|---|
| kimi-k2.7-code | 34.06 | 34.83 | 31.26 | +0.77 (noise) | −2.80 | ±1.43 |
| qwen3-coder:30b | 33.43 | 33.19 | 24.95 | −0.24 (noise) | −8.48 | ±0.74 |

**Key takeaway:** the `trimmed` (guidance-only) prompt was *neutral* — within run-to-run noise
of baseline for both models. The verbatim `full` prompt *hurt*, driven by its ~28.7k-token bulk
and by phantom tool calls (the prompt references tools the models don't have). So the current
`trimmed` prompt adds no measurable value. **Your mission is to design a better one.**

## Your mission

1. **Review the Session-1 outputs** to see where `trimmed` is weak/neutral and where models lose
   points. Read `results/REPORT.md` (per-criterion deltas), skim `results/scores/*.yaml` and a
   sample of `results/raw_outputs/*__trimmed__*.md`. The discriminating tasks are `api-design`,
   `refactor-nested`, `sql-query`, `explain-concise`, `tool-probe` (the trivial ones ceiling at 5).
   NOTE: if `results/` is empty (cleared since), regenerate with the pipeline below, or rely on
   `FINDINGS.md`. The current trimmed prompt is `system-prompts/fable-5-trimmed.md`.

2. **Research system-prompt architecture best practices for leading models.** Use WebSearch +
   WebFetch and the context7 MCP (for Anthropic docs at docs.claude.com). Cover: Anthropic prompt
   engineering, OpenAI/Google prompting guides, and — important — **model-specific** guidance for
   the actual targets (Qwen3-Coder and Kimi/Moonshot K2 prompting). The `deep-research` skill is
   available for a structured pass. Capture concrete, citable techniques (role framing, structure,
   positive imperatives, output-format specs, few-shot, reasoning guidance, constraint emphasis).
   Write a short `research/system-prompt-best-practices.md` with findings + sources.

3. **Design `system-prompts/trimmed-v2.md`** applying that research. Design constraints derived
   from Session-1 findings (do not ignore these — they are why v1 failed to help):
   - **Keep it short.** Length/bulk hurt, especially the smaller local model. Target well under
     ~1.5k tokens.
   - **Zero references to tools/capabilities the model lacks** (no web_search, files, memory,
     artifacts, MCP, bash). These caused phantom `<invoke ...>` calls that tanked `tool_discipline`
     and the tool-tempting tasks. If anything, instruct the model to answer directly in text and
     never emit tool-call syntax.
   - **Target the criteria where points were lost:** exact instruction-following (honor signatures,
     allowed libraries, output format, and length limits like "exactly 2 sentences"), conciseness
     (no padding/preamble/prompt-restating), correctness, and clean idiomatic code.
   - It must be a genuine, research-informed improvement over both `baseline` and current `trimmed`
     — the bar is beating current `trimmed` beyond the noise floor.

4. **A/B test current `trimmed` vs `trimmed-v2`** for BOTH models using the existing pipeline,
   then **blind-judge** and report. The winning question: does `trimmed-v2 − trimmed` exceed each
   model's noise floor, per total and per criterion?

## The pipeline (already built; in `harness/`)

Run from `harness/`. The Moonshot key is already in `harness/.env` (gitignored — never commit it).

```
# 0. Optional: archive Session-1 results you want to keep, then clear for a clean run
#    (results/ is gitignored & regenerable; FINDINGS.md already summarizes Session 1)
#    rm results/raw_outputs/*.md results/autocheck/*.yaml results/scores/*.yaml results/REPORT.md ; rm -rf results/blind/*

# 1. generate -> results/raw_outputs/{model}__{cond}__{task}__rN.md (+metadata)
python run_experiment.py --config config.yaml

# 2. objective correctness on testable tasks (extracts code even from phantom tool blocks)
python autocheck.py

# 3. build the blind judging set (labels stripped, shuffled) + sealed _map.json
python prepare_blind.py --seed 1

# 4. JUDGE (see below) -> results/blind/verdicts.yaml

# 5. de-anonymize verdicts -> results/scores/*.yaml ; then build the report
python deblind_merge.py
python score_report.py        # -> results/REPORT.md
```

### Config changes for the 2-condition A/B
Edit `harness/config.yaml` `prompts:` to contain ONLY the two conditions under test, so the run
is focused and cheap:
```yaml
prompts:
  trimmed:    ../system-prompts/fable-5-trimmed.md
  trimmed_v2: ../system-prompts/trimmed-v2.md
```
Keep the existing per-model `repeats` (qwen 3, Kimi 5) and decoding (Kimi is force-pinned to
`temperature: 1`, `top_p: 0.95` — leave that override in place). Then **edit
`harness/score_report.py`**: set `CONDITIONS = ["trimmed", "trimmed_v2"]` and `BASELINE = "trimmed"`
so the headline delta is `trimmed_v2 − trimmed` (the report code is otherwise condition-agnostic).
(If you instead use `run_experiment.py --prompt`, add `trimmed_v2` to its argparse `choices`.)

### Judging (you are the blind judge)
Reproduce Session-1's approach: spawn ~6–8 **parallel Claude subagents** (Agent tool,
`subagent_type: claude`), each assigned a disjoint range of `results/blind/c*.md`, each writing
`results/blind/verdicts_partNN.yaml`, then merge: `cat verdicts_part*.yaml > verdicts.yaml`.
Give every judge the rubric from `rubric/AB_TESTING_RUBRIC.md` (7 criteria, 0–5) and these rules:
- **Blind:** read ONLY your assigned `cNNN.md` files; do NOT read `results/blind/_map.json`.
- **Correctness scores the code itself**, regardless of delivery; a phantom tool call is penalized
  ONLY in `tool_discipline` (and maybe instruction_follow/conciseness) — never double-count.
- Use the full 0–5 range; don't default to 5. Output the exact per-case YAML schema (see Session-1
  judge prompts / `results/scores/_TEMPLATE.yaml.example`).

## Hard-won gotchas (don't rediscover these)
- **Ollama context:** stock `qwen3-coder:30b` defaults to `num_ctx=4096` and silently truncates
  long prompts. Config already points at `qwen3-coder-fable:30b` (num_ctx 40960; build file
  `harness/Modelfile.qwen-fable`). Your v2 prompt is small so truncation won't bite, but keep using
  that model for consistency. Confirm it exists: `ollama list`.
- **Kimi API** rejects `temperature≠1` and `top_p≠0.95` — already handled by a per-model override.
- **Secrets:** `MOONSHOT_API_KEY` lives in `harness/.env` (auto-loaded, gitignored). Never commit it.
- **Clean stale outputs** before a run — repeats use `__rN` suffixes, so an old unsuffixed file from
  a `--repeats 1` run lingers as an extra sample.
- `results/` (raw_outputs, autocheck, scores, blind, REPORT) and `results/blind/` are gitignored.
- Commit code/docs (not results) only when asked; end commit messages with the Co-Authored-By line.

## Deliverables
- `research/system-prompt-best-practices.md` (findings + sources)
- `system-prompts/trimmed-v2.md` (the optimized prompt)
- `results/REPORT.md` for the trimmed-vs-trimmed_v2 A/B (both models, blinded)
- An update to `FINDINGS.md` (or a `FINDINGS-v2.md`) stating whether v2 beat v1 beyond the noise
  floor, per model and per criterion, with the honest caveats (small n; Kimi temp=1 noise; judge
  is an LLM). Estimated Moonshot cost for this A/B is small (~$0.10–0.20; both prompts are tiny).

Start by reading the orientation files and `results/REPORT.md`, then propose the research plan and
the v2 design rationale before running the (cheap) A/B.
