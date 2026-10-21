---
name: setup-pstack
description: Configure which models pstack uses per role and at what reasoning budget. Detects your available models and writes an always-applied rule that overrides the skill defaults. Use for /skill:setup-pstack, "configure pstack models", "pstack budget", or changing pstack's model choices.
---

# Setup pstack

This copy is generated for Pi and already uses Pi tool names. Read [the Pi adapter](~/.agents/pstack/docs/harness/pi.md) once per session for the rows a generated tree cannot change: subagent capability, isolation, model roles, and session transcripts.

Write `~/.pi/agent/pstack-models.md`, the role file that sets pstack's model per role. Pi loads no rules directory, so read it when a skill names a role.

## Steps

### 1. Detect available models

Enumerate the model ids available to an agent file in this session with `pi --list-models`. That is the dependable source. If the command fails, ask the user to paste the ids they have access to. Never write a real id you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected ids.

### 2. Load current state

The default role-to-model mapping is the file shape shown in step 5 below. If `~/.pi/agent/pstack-models.md` already exists, read it and treat its `# budget` line and its role values as the current choices. Otherwise start from those defaults. A line whose role is not in step 5, such as `how critics`, is from a retired role. Drop it.

### 3. Budget, map, and confirm

**(a) Ask for a budget.** Prefer `question` over free text. Offer these four options with these exact labels, and name the current budget when the file records one. With no file, say that `large` matches the skill defaults.

- `unlimited — max reasoning`
- `large — xhigh reasoning`
- `medium — high reasoning`
- `small — medium reasoning`

**(b) Apply it.** Build the working table from the role defaults. The defaults in this skill are pstack's portable Cursor slugs, not Pi model ids. On Pi, replace each with a detected id of the same tier: a fast, cheap model for code roles and the strongest judgment model for prose and judgment. Add a `:<thinking>` suffix when the role needs a level other than the model default, for example `anthropic/claude-opus-5-5:xhigh`. `inherit-parent` and `auto` do not change. If no detected id fits a role, mark it as needing a choice.

**(c) Show the roles and confirm.** Show every role with its model, marking any real id not in the detected set as needing a choice. Also list each line step 2 dropped. Ask whether to accept as-is or change specific roles, offering the detected models plus `inherit-parent` and `auto` (both mean: this role runs on the parent chat model) as the options. Prefer `question` over free text. For panel roles (arena runners, architect runners, interrogate reviewers) the value is a list, and one subagent runs per entry, alias entries included, so the list length sets the count. `arena cross-judge pool` is also a list, but Arena selects one value from it whose model family differs from the parent's when possible. `swarm workers` is the default model for every worker unless a race or comparison assigns another model per arm.

### 4. Validate

Every real id written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real id is not available, stop and ask again.

### 5. Write the file

Write `~/.pi/agent/pstack-models.md` with a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels tomato-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:

```
# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# Values are Pi model ids: <provider>/<model>, with an optional :<thinking> suffix.
# `inherit-parent` or `auto` runs the role on the parent chat model (an agent with no `model` field).
# budget: large (xhigh)
feature, refactoring: <fast code id>
bug-fix: <fast code id>
perf-issue: <fast code id>
hillclimb: <fast code id>
judgment and prose: <strong judgment id>
hardest tasks: <strong judgment id>
how explorer: <fast code id>
how explainer: <strong judgment id>
why investigators: <fast code id>
why synthesizer: <strong judgment id>
reflect tooling: <fast code id>
reflect judgment, divergent, synthesizer: <strong judgment id>
arena runners: <strong judgment id>, <fast code id>
arena cross-judge pool: <strong judgment id>, <fast code id>
swarm workers: <fast code id>
architect runners: <strong judgment id>, <fast code id>
interrogate reviewers: <strong judgment id>, <fast code id>
```

### 6. Confirm

Tell the user the file was written and that it applies to new sessions. Each role binds to an agent file: a role takes effect only when a file under `~/.pi/agent/agents/` names its model. Re-running this skill updates the file.

### 7. Offer a verification skill (optional)

Check whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /skill:create-verification-skill." On yes, invoke `/skill:create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.
