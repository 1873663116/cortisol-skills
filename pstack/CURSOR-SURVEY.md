# Cursor residue survey (`skills/`)

Scope: `/Users/xiongzhipeng/.agents/skills/`. Report only. Skipped: `subagent_type`, model slugs, `setup-pstack`. Sorted by damage if left alone.

**Totals (approx.):** ~59 lines matching `Cursor` / `.cursor/` in skill prose and shell (excluding GraphQL `endCursor` / login noise). ~22 `.cursor/` path mentions. Most of the rest are cosmetic (see bottom).

---

## Category 1 — Dead write targets (exhaustive)

These instruct creating or updating state under Cursor skill roots. Claude Code, Codex CLI, and Grok CLI do not load skills from those paths, so the work is burned.

| Severity | File | Line | What it does | Should say instead |
|---|---|---:|---|---|
| **Critical** | `skills/create-verification-skill/SKILL.md` | 9, 25, 36 | Generates the whole project verification skill and feature map under `.cursor/skills/verify-<app>/`. | Write under the host’s project skill root that actually registers (e.g. `.agents/skills/`, `.claude/skills/`, `.codex/skills/`, or the repo’s configured skills dir); name the path once and keep create + maintain aligned. |
| **Critical** | `skills/automate-me/SKILL.md` | 69 | Drafts the personal `*-mode` skill to `.cursor/skills/<handle>/…`, `.cursor/skills/<handle>-mode/`, or `~/.cursor/skills/…`. | Same: write to the active host skill root (`~/.agents/skills/`, user Claude/Codex/Grok skill dirs, or the project skill path the host loads). |
| **High** | `skills/maintain-verification-skill/SKILL.md` | 25 | Locates the skill to edit as “usually `.cursor/skills/verify-*/`”, then edits that tree. | Locate by content (launch/drive + feature map) across host skill roots; default glob should match where `create-verification-skill` writes after the fix above. |
| **High** | `skills/automate-me/SKILL.md` | 17 | Searches only `.cursor/skills/**/*-mode/` and `~/.cursor/skills/*-mode/` before update-in-place. | Search the same host skill roots used for writes; otherwise “update my mode” misses the live skill and creates a second dead copy. |

No other `skills/` text tells the agent to **write** a `.cursor/` path. Reads of `~/.cursor/rules/pstack-models.mdc` and transcript trees are not write targets (category 2 / cosmetic).

---

## Category 2 — Behavioural dependency (brief)

One sentence each: what Cursor supplied → what a local substitute needs.

| Damage | File:line | Cursor supplied | Local substitute |
|---|---|---|---|
| **Critical** | `tomato-mode/playbooks/autopilot-full.md:6,10`; `shipping.md:7`; `orchestrate.md:19,97` | Cloud agents + dashboard status/liveness + cloud-sleeper wake chains. | Host subagents or remote workers with a documented status API; or drop cloud ownership and run PR owners as local subagents with PR/branch identity only. |
| **Critical** | `tomato-mode/playbooks/autonomous-run.md:6`; also `bug-fix.md:8`, `babysit.md:14`, `shipping.md:17`, `visual-parity.md:8` | Built-in `/loop` wake/rearm for long polls. | Host scheduler/monitor, explicit watcher subagent + rearm instructions, or a small local poll script the skill owns. |
| **Critical** | `recall/SKILL.md:15` (+ fan-out steps) | Multi-chat JSONL corpus at `~/.cursor/projects/<slug>/agent-transcripts/…`. | See **Verdict: recall** below. |
| **High** | `reflect/SKILL.md:25–31`; `automate-me/SKILL.md:29`; `show-me-your-work/SKILL.md:56`; `tomato-mode/playbooks/session-pickup.md:7`, `eval.md:24` | System-prompted workspace `agent-transcripts/` (and ban on globbing other `~/.cursor/projects/*`). | Per-host transcript/session path discovery; fail closed if the host has no durable multi-session log. |
| **High** | `tomato-mode/scripts/worktree-audit.sh:25–27` | Hard-coded `$HOME/.cursor/projects/$slug/agent-transcripts` for “newest chat touched this worktree”. | Inject host transcript root, or skip the chat-age signal when absent. |
| **High** | `why/SKILL.md:100` | “Cursor environment” tool map / `mcps/` tree for enabled MCP servers. | List tools/MCPs the current host exposes (Executor search, env tool list, or host docs); never assume a Cursor `mcps/` dir. |
| **Medium** | `tomato-mode/playbooks/opening-a-pr.md:9`; `SKILL.md:27`; `babysit.md:3`; `references/plan.md:101` | Cursor built-in babysit skill vs tomato-mode babysit routing. | Drop the Cursor-skill comparison; always route PR-status requests to `playbooks/babysit.md`. |
| **Medium** | `tomato-mode/playbooks/orchestrate.md:17`, `reflect/SKILL.md:37`, `interrogate/SKILL.md:36` | Cursor `Task` tool as the only spawn/resume bus. | Host subagent/spawn primitive (name it generically: “spawn N parallel subagents”). |
| **Low** | `arena/SKILL.md:28,41`; `swarm/SKILL.md:25`; `interrogate/SKILL.md:36` | Optional model pools in `~/.cursor/rules/pstack-models.mdc`. | Optional host-neutral config (e.g. under `~/.agents/` or env); defaults already exist when the file is missing. |
| **Low** | `automate-me/SKILL.md:17,44`; poteto AskUserQuestion refs | Cursor `AskUserQuestion` tool. | Host structured-question tool, or plain multi-choice in chat. |

---

## Verdict: `skills/recall/SKILL.md`

**As written: broken off Cursor.** The only durable chat corpus it names is Cursor’s per-project `agent-transcripts` JSONL tree. The shared-record half (via **why**) still works; the chat-history half does not.

**Local substitute?** Only if the host keeps multi-session logs an agent can search:

- Claude Code / Codex / Grok: possible if session history files are on disk and path rules are documented per host; none of those paths appear in this skill today.
- Git, `gh`, tickets, and **why** cover the *shared* record but not “what I decided in yesterday’s chats.”

**Recommendation:** Do not keep the skill in its current form. Either (a) rewrite step 3 to discover the active host’s transcript root and format, and fail closed with a clear message when none exists, or (b) **drop/disable** `recall` until that rewrite lands. Prefer (a) if multi-session history is a real product need; prefer (b) if users only need branch/PR/ticket catch-up (session-pickup + **why** already cover slices of that).

---

## Verdict: `pstack/automations/benny/`

**Drop for this stack.** Benny installs into a target repo’s `.cursor/automations/benny/`, enables pstack via `.cursor/settings.json`, finishes through Cursor’s built-in `/automate` + Automations editor, and expects Cursor Slack actions and the Cursor automation runtime to fire triage/repro prompts. Nothing in the Claude Code / Codex / Grok skill load path reads those trees or schedules those automations. Keep the triage/repro *skill bodies* only if you re-host them as ordinary skills driven by a non-Cursor scheduler (Slack bot + CI, etc.); as a Cursor automation pack, it has no local counterpart. Do not spend porting effort on setup-benny path surgery alone.

---

## Cosmetic (not listed)

**~45** remaining Cursor / `.cursor/` hits are harmless prose: package name `@cursor-skill/…`, “cursor location” for vague targets, worktree path *awareness* (`.cursor/worktrees/…`), “don’t use Cursor’s babysit” restated as product voice, Cursor app cache cleanup tips, reflect reviewer path examples under `.cursor/skills/`, and `quota-axi` listing Cursor as a quota provider. No write target and no required runtime. Fix opportunistically when touching those files; no dedicated pass needed.
