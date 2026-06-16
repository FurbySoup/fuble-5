# System prompts

The two conditions of the experiment. **Freeze both before scoring begins.**

| File | Role | Notes |
|------|------|-------|
| `baseline.md` | **Before** condition | A minimal, neutral coding-assistant prompt. Identical for both models so the only difference vs. Fable 5 is the prompt content itself. |
| `fable-5-full.md` | **After** condition | Verbatim Claude Fable 5 system prompt (1,808 lines), downloaded from [saynchowdhury/claude-fable-5-system-prompt](https://github.com/saynchowdhury/claude-fable-5-system-prompt). Not modified. |

## Important caveat

`fable-5-full.md` is Anthropic's *internal* prompt. It references tools and surfaces the
candidate models don't have: `web_search`, `web_fetch`, `bash_tool`, `create_file`,
artifacts, MCP connectors, persistent memory, the claude.ai product, etc. We feed it
**unmodified on purpose** — observing how a foreign model reacts to that scaffolding
(criteria 6 & 7 in the rubric) is part of the experiment.

If you later want a cleaner test of *just* the behavioral/style guidance, create a third
condition (`fable-5-trimmed.md`) with tool sections removed, and run it as an additional
column. Document any trimming precisely so it stays reproducible.
