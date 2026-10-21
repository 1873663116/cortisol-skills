---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes an always-applied rule that overrides the skill defaults. Use for /setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

This copy is generated for DeepSeek Harness and already uses DSH tool names. Read [the DSH adapter](../../../../docs/harness/deepseek.md) once per session for the rows a generated tree cannot change: subagent capability, isolation, model roles, and session transcripts.

Write pstack's model roles into `~/.agents/AGENTS.md`, the user-global instruction file this harness loads into every session. Replace only the delimited pstack region and leave the rest of that file alone.

## Steps

### 1. Detect available models

Call `list_subagent_models`. It reports the exact provider and model routes this session may name, which is the only dependable source. If the tool is absent, model selection is off for this composition, so say so and leave the role table on its defaults. Never write a route you have not confirmed. The aliases `inherit-parent` and `auto` are always valid even though they are not routes.

### 2. Load current state

The default role-to-model mapping is the shape shown in step 5 below. If `~/.agents/AGENTS.md` already holds a pstack region, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer `ask_user_question` over free text. Offer these three options with these exact labels, and name the current budget when the region records one. With no region, say that `large` matches the skill defaults.

- `unlimited: max reasoning`
- `large: high reasoning`
- `small: low reasoning`

**(b) Apply it.** The budget sets `reasoning_effort`, and only on routes that declare efforts. In this deployment the `deepseek*` routes declare `max`, `high`, and `low`; every other route ignores the setting. Build the working table from the skill defaults, and on a re-run keep any role you changed by route (`inherit-parent`, `auto` included). `unlimited` sets every role to `max`, `large` to `high`, `small` to `low`. Keep each role's route, so a diverse panel stays diverse. `inherit-parent` and `auto` do not change.


**(c) Show the roles and confirm.** Show every role with its model, marking any route not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model, which is how Auto users stay on Auto) as the options. Prefer `ask_user_question` over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every route written must appear in what `list_subagent_models` returned. `inherit-parent` and `auto` always pass. If a chosen route is not available, stop and ask again.

### 5. Write the rule

Write the region into `~/.agents/AGENTS.md` between `<!-- pstack-models:start -->` and `<!-- pstack-models:end -->`. Replace only that region so the rest of the file survives, and append it when missing. Shape:

```
<!-- pstack-models:start -->
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# A value is a provider and model as `list_subagent_models` reports them, written `provider / model`. `inherit-parent` or `auto` runs the role on the parent model.
# budget: large (high)
feature, refactoring: command-code / deepseek/deepseek-v4.1-flash
bug-fix: command-code / deepseek/deepseek-v4.1-flash
perf-issue: command-code / deepseek/deepseek-v4.1-flash
hillclimb: command-code / deepseek/deepseek-v4.1-flash
judgment and prose: command-code / gpt-6-luna
hardest tasks: command-code / gpt-6-luna
how explorer: command-code / deepseek/deepseek-v4.1-flash
how explainer: command-code / gpt-6-luna
why investigators: command-code / deepseek/deepseek-v4.1-flash
why synthesizer: command-code / gpt-6-luna
reflect tooling: command-code / deepseek/deepseek-v4.1-flash
reflect judgment, divergent, synthesizer: command-code / gpt-6-luna
arena runners: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash
arena cross-judge pool: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash
swarm workers: command-code / deepseek/deepseek-v4.1-flash
architect runners: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash
interrogate reviewers: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash
<!-- pstack-models:end -->
```

### 6. Confirm