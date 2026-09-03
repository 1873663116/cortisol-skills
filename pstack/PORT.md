# Porting pstack

pstack is a Cursor plugin. This repo runs its skills under Claude Code, Codex CLI and Grok CLI, which share a skills directory but none of Cursor's runtime. Every difference between upstream and `skills/` follows one of the rules below.

The rules are the unit of maintenance. When upstream moves, `scripts/check-upstream.py` says which files changed and whether this fork had touched them; for the ones it had not, re-apply these rules to the new text and the merge is done. `UPSTREAM` pins the baseline the script compares against.

## Layout

Upstream `pstack/skills/<name>` becomes `skills/<name>`, so every harness that scans a skills directory finds them. Three exceptions:

- `tdd` is `tdd-bug-fix`. The name collided with an existing skill that covers what makes a test worth keeping; upstream's is a seven-step bug-fix workflow. Both survive.
- `setup-pstack` is not installed. It writes `~/.cursor/rules/pstack-models.mdc`, and the role table it generated now lives in `skills/dispatch/`, edited directly.
- `autopilot-stack` is deleted. Its premise is a linear Graphite stack; this setup uses plain GitHub, and a faked substitute reads worse than an absent playbook.

`pstack/` holds what is not a skill: these notes, the upstream pin, the sticky-mode hook, the uninstalled `setup-pstack`, the `agents/` prompt files, and upstream's docs. Upstream's `docs/guide/` stays as archived reference for update reconciliation; it teaches Cursor's install paths and is not local truth.

## Renames

| Upstream | Here | Why |
|---|---|---|
| `AskQuestion` | `AskUserQuestion` | Tool name |
| `create-skill` | `writing-for-agents` | Cursor built-in; this repo's own skill covers it |
| `deslop` | `unslop` | Shipped in an unported Cursor plugin; `unslop` covers the ground |
| `~/.cursor/rules/pstack-models.mdc` | `skills/dispatch/` role table | The config that file held |
| `.cursor/skills/` | `skills/` for user-level, `.claude/skills/` for project-local | Nothing reads the Cursor path |
| `~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl` | `~/.claude/projects/<slug>/<uuid>.jsonl` | Same slug rule, one less directory level |
| `poteto-mode` | `tomato-mode` | Local name of the routing skill |
| `poteto-agent` | `tomato-agent` | Local name of the style subagent |

## Rewrites

**Delegation.** Upstream calls Cursor's `Task` tool with `subagent_type`, a per-role model slug, `run_in_background: true`, and a readonly agent mode. Here every delegation runs through Orca orchestration (`skills/orchestration/`): Orca creates the task, dispatches the worker, and carries the concurrency, waiting and resume semantics. `skills/dispatch/` is the single authority on the carrier, the role matrix and the role→model table; other skills name a role and point at it. Roles that relied on readonly to keep a reviewer from writing carry that instruction in the prompt. Worktree isolation for write-side workers comes from Orca's worktree mechanism rather than a tool parameter.

**Model and effort.** Effort stays a worker-side property. The per-role model table in `skills/dispatch/` is backfilled from upstream `setup-pstack`'s default matrix (re-checked against `cursor/plugins@6fecddb`, 2026-08-27) with local substitutions: Grok→`GLM 5.3 Flash`, Fable→`claude-opus-5`, Codex unchanged. Panel seats keep only distinct model families, so upstream's four-seat panels collapse to three. `~/.cursor/rules/pstack-models.mdc` predates this and is no longer read by anything here.

**Routing economics.** Upstream sends bulk work to its cheapest per-token model, because Cursor bills every model as API usage. Here the agents are subscriptions, so the constraint is pool size and reset cadence, not unit price. Volume therefore sits on the largest pool rather than the cheapest token, and the fan-out tier is spent in order of how soon its headroom expires. `skills/dispatch/` carries the current order; treat it as policy that changes when budgets do, separately from the role definitions it sits beside.

**Sticky mode.** Upstream marks `poteto-mode` with `mode: true` and a `reminder:` field that Cursor re-injects each turn. Neither key exists elsewhere. Locally the skill is `tomato-mode`. `pstack/hooks/tomato_mode.py` runs on `UserPromptSubmit`, sets a per-session state file when it sees `/tomato-mode` or `$tomato-mode` in the raw prompt (Claude Code submits the slash form, T3 Code rewrites the same keystroke to `$`), and re-injects `pstack/hooks/reminder.txt` on later turns. On the activation turn it also emits a line pointing at the SKILL.md path, because the harness expands the command into the skill body only when it leads the message; a mid-message mention arrives as bare text, and `disable-model-invocation` keeps the skill out of the model's listing, so the path is the model's only way in. The hook reads the field `prompt`; Anthropic's own hook documentation calls it `user_prompt` and is wrong. `disable-model-invocation` needs no translation, Claude Code honours it.

**Capability gaps, stated rather than substituted.** `control-cli` and `control-ui` shipped in an unported Cursor plugin. Browser, Electron and web UI work routes to the `playwright` skill. Nothing here drives a CLI or TUI, so those sites say to drive it by hand rather than send the reader hunting.

**Subagent style.** Upstream ships `agents/poteto-agent.md`. Locally that file is `agents/tomato-agent.md`; its body tells every spawned delegate to read tomato-mode in full before working. `delegate_to_agent` has no agent definitions, so the same instruction now travels as a mandatory prompt prefix on Judgment and Letter-precise delegations; the rule lives in `skills/dispatch/`. `agents/comment-sicko.md` stays here as a prompt file that the `no-comments` skill points delegates at.

**Transcript-reading scripts.** `worktree-audit.sh` computes the local transcript directory (`~/.claude/projects/<slug>`, slug = absolute path with `/` and `.` replaced by `-`). `watch-pr` and `orch` run on Bun with `gh` and needed no changes; both smoke-tested.

## Shelved

Graphite. Roughly twenty `gt` invocations across `shipping`, `babysit` and `autopilot-full`. Deliberately not rewritten: the active repositories here commit straight to `main` with no open PRs, so the PR-driving playbooks have nothing to drive. If a PR workflow appears, translate `gt` to `git` and `gh` then.

Roughly 45 mentions of the word "Cursor" that are prose and execute nothing. `CURSOR-SURVEY.md` has the classified inventory.

## Dropped

`automations/benny/`, deleted 2026-08-09. A Slack triage-and-fix automation whose install surface, triggers and I/O all live on Cursor Automations and Slack actions; the loop logic was the only portable part, and nothing here runs that workflow. Re-pullable from upstream if that changes.

`playbooks/orchestrate.md`, deleted 2026-08-09. Its coordination core manages many parallel stacked PRs, and a survey of the main workspace (EnchronWorkspace, 74k LOC Swift) found a single working branch and zero open PRs, so the thing it coordinates does not exist here. Multi-day work over a large codebase routes to `figure-it-out` and `autonomous-run` instead. The bookkeeping CLI it used (`tomato-mode/scripts/orch/`) is portable and stays.
