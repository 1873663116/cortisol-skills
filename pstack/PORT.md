# Porting pstack

Upstream ships pstack twice. `pstack/` is the Cursor plugin. `harness/pstack/claude-code/` is a generated copy for Claude Code that already carries the adapter line in every skill that uses Cursor names, the guide, and the README. This repo ports the generated copy, so the work is a small set of path and name transforms, not a hand rewrite.

`skills/` is a symlink target: `~/.claude/skills` points at it, so every skill here loads in Claude Code without the plugin system. `pstack/` holds what is not a skill: these notes, the upstream pin, the adapter, the guide, the agent prompts, and the plugin manifests.

## Updating

`scripts/check-upstream.py` compares the pinned commit in `UPSTREAM` against a fetched upstream and sorts each changed file:

| Bucket | Meaning | Action |
|---|---|---|
| TAKE | Upstream changed it; the local copy matches what the transforms produce from the old baseline. | Apply the transforms and write it over. |
| REVIEW | Upstream changed it and the local copy diverged. | Reconcile by hand, then fold any lasting difference into the transforms. |
| NEW | A file upstream added. | Add it through the transforms. |
| GONE | Upstream deleted a file this fork still carries. | Delete it, or record why it stays under Dropped. |

The script applies the same transforms the port uses, so a TAKE file is mechanical. Run it, port the buckets, then update `UPSTREAM` to the new commit and version.

## Transforms

`scripts/check-upstream.py` encodes these, and they are the whole port:

- **Skill folders.** `poteto-mode` is `tomato-mode`; `poteto-help` is `tomato-help`. Every occurrence in prose, frontmatter, cross-links, package names, and install keys follows. `poteto-agent` is `tomato-agent`, and `agents/poteto-agent.md` is `agents/tomato-agent.md`.
- **Guide filename.** `docs/guide/02-poteto-mode.md` is `docs/guide/02-tomato-mode.md`, and links to it follow.
- **Link depth.** The generated tree roots links at the plugin folder, so its skills reach the guide with `../../docs/`. Here `skills/` sits one level higher than `pstack/`, so those links become `../../pstack/docs/`, `../../pstack/README.md`, and guide links to skills become `../../../skills/`.
- **Adapter line.** The generated tree opens each skill that uses Cursor names with a line pointing at the adapter. This fork keeps the pointer and states that the adapter maps Cursor names onto Claude Code.

## Claude Code adapter

`docs/harness/claude-code.md` carries the mapping, and it is upstream's file with the poteto names changed. It covers:

- **Tools.** `Task` is `Agent`, `AskQuestion` is `AskUserQuestion`, and a skill is reached by reading its `SKILL.md` because the `Skill` tool refuses most of them.
- **Subagents.** `generalPurpose` is `general-purpose`, `readonly: true` is the `Explore` type, and `environment: "cloud"` is an `isolation: "worktree"` run. `poteto-agent` and `comment-sicko` are `pstack:poteto-agent` and `pstack:comment-sicko` as plugin agents; this repo installs the same files as plain agent prompts in `pstack/agents/`.
- **Models.** A Cursor model slug becomes an `Agent` `model` and `effort`. Non-Claude slugs drop `model` so the delegate runs on the session model.
- **Paths.** Cursor skill roots, plugin roots, rules, and the transcript tree map to their `~/.claude/` equivalents.
- **Cursor-only features.** Automations, Bugbot, cloud agents, and the built-in PR tool have no counterpart. A step that needs one writes `Skipped in Claude Code: <step>. <reason>.` and continues.

`setup-pstack` writes model roles to `~/.claude/rules/pstack-models.md`, which Claude Code loads into every session.

## Sticky mode

Upstream dropped the `mode` and `reminder` frontmatter keys in 0.15.23 because Cursor ignored them, and ships no hook. This repo has no hook either: `tomato-mode` loads as an ordinary skill and answers `/tomato-mode` by name. `archive/tomato-mode-claude-code-support/hooks/` keeps the retired `UserPromptSubmit` hook that re-injected the reminder each turn, in case the mode needs to persist without an explicit invocation again.

## Not carried

- **Automations.** `automations/benny/` runs on Cursor Automations, routine `update_state` calls, and Slack actions. Nothing here runs that workflow. The README and guide name it descriptively instead of linking to a local copy.
- **The Cursor plugin manifests and marketplace.** `pstack/.claude-plugin/plugin.json` and `plugin.json` are kept as upstream ships them, so the port can become a plugin install later. Loading today is through the skills symlink.

## Local skills

Eight skills in `skills/` are not pstack's: `find-skills`, `grilling`, `handoff`, `mole`, `prompt-engineering`, `subagent-dispatch`, `writing-for-agents`, `wtf`. They are outside the update loop, and `check-upstream.py` never reports them.
