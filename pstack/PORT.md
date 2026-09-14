# Porting pstack

pstack is a Cursor plugin. This repo runs its skills under Claude Code, Codex CLI and Grok CLI, which share a skills directory but none of Cursor's runtime. Every difference between upstream and `skills/` follows one of the rules below.

The rules are the unit of maintenance. When upstream moves, `scripts/check-upstream.py` says which files changed and whether this fork had touched them; for the ones it had not, re-apply these rules to the new text and the merge is done. `UPSTREAM` pins the baseline the script compares against.

## Layout

Upstream `pstack/skills/<name>` becomes `skills/<name>`, so every harness that scans a skills directory finds them. Three exceptions:

- `tdd` is `tdd-bug-fix`. The name collided with an existing skill that covers what makes a test worth keeping; upstream's is a seven-step bug-fix workflow. Both survive.
- `setup-pstack` is not installed. Its Cursor model configuration is not used here.
- `autopilot-stack` is deleted. Its premise is a linear Graphite stack; this setup uses plain GitHub, and a faked substitute reads worse than an absent playbook.

`pstack/` holds what is not a skill: these notes, the upstream pin, the sticky-mode hook, the uninstalled `setup-pstack`, the `agents/` prompt files, and upstream's docs. Upstream's `docs/guide/` stays as archived reference for update reconciliation; it teaches Cursor's install paths and is not local truth.

## Renames

| Upstream | Here | Why |
|---|---|---|
| `AskQuestion` | `AskUserQuestion` | Tool name |
| `create-skill` | `writing-for-agents` | Cursor built-in; this repo's own skill covers it |
| `deslop` | `unslop` | Shipped in an unported Cursor plugin; `unslop` covers the ground |
| `.cursor/skills/` | `skills/` for user-level, `.claude/skills/` for project-local | Nothing reads the Cursor path |
| `~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl` | `~/.claude/projects/<slug>/<uuid>.jsonl` | Same slug rule, one less directory level |
| `poteto-mode` | `tomato-mode` | Local name of the routing skill |
| `poteto-agent` | `tomato-agent` | Local name of the style subagent |

## Rewrites

**Delegation.** Use the Agent tool. Each skill defines the roles, task scope, and acceptance criteria. Read-only assignments state `Do not write or modify files`; concurrent writers use separate worktrees or file scopes.

**Codex hook.** Register the existing `UserPromptSubmit` script using [hooks/README.md](hooks/README.md).

**Sticky mode.** Upstream marks `poteto-mode` with `mode: true` and a `reminder:` field that Cursor re-injects each turn. Neither key exists elsewhere. Locally the skill is `tomato-mode`. `pstack/hooks/tomato_mode.py` runs on `UserPromptSubmit`, sets a per-session state file when it sees `/tomato-mode` or `$tomato-mode` in the raw prompt (Claude Code submits the slash form, T3 Code rewrites the same keystroke to `$`), and re-injects `pstack/hooks/reminder.txt` on later turns. On the activation turn it also emits a line pointing at the SKILL.md path, because the harness expands the command into the skill body only when it leads the message; a mid-message mention arrives as bare text, and `disable-model-invocation` keeps the skill out of the model's listing, so the path is the model's only way in. The hook reads the field `prompt`; Anthropic's own hook documentation calls it `user_prompt` and is wrong. `disable-model-invocation` needs no translation, Claude Code honours it.

**Capability gaps, stated rather than substituted.** `control-cli` and `control-ui` shipped in an unported Cursor plugin. Browser, Electron and web UI work routes to the `playwright` skill. Nothing here drives a CLI or TUI, so those sites say to drive it by hand rather than send the reader hunting.

**Subagent style.** Skills pass role-specific instructions in the Agent task. `agents/comment-sicko.md` supplies the review prompt used by `no-comments`.

**Transcript-reading scripts.** `worktree-audit.sh` computes the local transcript directory (`~/.claude/projects/<slug>`, slug = absolute path with `/` and `.` replaced by `-`). `watch-pr` and `orch` run on Bun with `gh` and needed no changes; both smoke-tested.

## Shelved

Graphite. Roughly twenty `gt` invocations across `shipping`, `babysit` and `autopilot-full`. Deliberately not rewritten: the active repositories here commit straight to `main` with no open PRs, so the PR-driving playbooks have nothing to drive. If a PR workflow appears, translate `gt` to `git` and `gh` then.

Roughly 45 mentions of the word "Cursor" that are prose and execute nothing. `CURSOR-SURVEY.md` has the classified inventory.

## Dropped

`automations/benny/`, deleted 2026-08-09. A Slack triage-and-fix automation whose install surface, triggers and I/O all live on Cursor Automations and Slack actions; the loop logic was the only portable part, and nothing here runs that workflow. Re-pullable from upstream if that changes.

`playbooks/orchestrate.md`, deleted 2026-08-09. Its coordination core manages many parallel stacked PRs, and a survey of the main workspace (EnchronWorkspace, 74k LOC Swift) found a single working branch and zero open PRs, so the thing it coordinates does not exist here. Multi-day work over a large codebase routes to `figure-it-out` and `autonomous-run` instead. The bookkeeping CLI it used (`tomato-mode/scripts/orch/`) is portable and stays.
