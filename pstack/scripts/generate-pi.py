#!/usr/bin/env python3
"""Generate the Pi tree from the pstack skills.

Pi reads skills from ~/.pi/agent/skills and ~/.agents/skills, so the generated
tree lives in its own root and Pi finds it first. Only tool names, field names,
paths, and host-specific mechanics are rewritten. Prose stays shared with the
Claude Code tree.

Usage:
  generate-pi.py            write the tree
  generate-pi.py --check    report drift and exit non-zero
"""

import argparse
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SOURCE = os.path.join(REPO, "skills")
OUT = os.path.join(ROOT, "generated", "pi", "skills")

LOCAL_ONLY = {
    "find-skills",
    "grilling",
    "handoff",
    "mole",
    "prompt-engineering",
    "subagent-dispatch",
    "writing-for-agents",
    "wtf",
}

SPAN = {
    "Task": "subagent",
    "AskQuestion": "question",
    "AskUserQuestion": "question",
    "TodoWrite": "todo",
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Grep": "grep",
    "Glob": "find",
    "Bash": "bash",
    "generalPurpose": "subagent",
    "Skill": "SKILL.md",
}

BARE = [
    (r"\bthe Task tool\b", "the `subagent` tool"),
    (r"\bthe Task subagent\b", "the `subagent` tool"),
    (r"\bTask subagent\b", "`subagent`"),
    (r"\bTask calls\b", "`subagent` calls"),
    (r"\bTask call\b", "`subagent` call"),
    (r"\bAskQuestion tool\b", "`question` tool"),
    (r"\bAskQuestion\b", "`question`"),
    (r"\bAskUserQuestion\b", "`question`"),
    (r"\bTodoWrite\b", "`todo`"),
    (r"\bthe `Skill` tool\b", "reading a `SKILL.md` file"),
    (r"\bthe Task\b", "`subagent`"),
    (r"(?<!<)\bTask\b", "`subagent`"),
]

FIELD_RULES = [
    (
        "the `Skill` tool",
        "reading a `SKILL.md` file",
    ),
    (
        "`Skill` tool",
        "reading a `SKILL.md` file",
    ),
    (
        "`subagent_type: generalPurpose`, `readonly: true`",
        "`subagent` on a read-only agent whose `tools` line is `read`, `grep`, `find`, `ls`",
    ),
    (
        "`subagent_type: generalPurpose`, `environment: \"cloud\"`, `run_in_background: true`",
        "`subagent` in a `git worktree` named in the brief",
    ),
    (
        "`subagent_type: generalPurpose`, `readonly: false`",
        "`subagent` on an agent with the full tool set",
    ),
    (
        "`subagent_type: generalPurpose`",
        "`subagent`",
    ),
    (
        "`subagent_type: \"tomato-agent\"`",
        "`subagent` with agent `tomato-agent`",
    ),
    (
        "`subagent_type: \"comment-sicko\"`",
        "`subagent` carrying `comment-sicko`'s instructions in the brief",
    ),
    (
        "`environment: \"cloud\"`",
        "a `git worktree` named in the brief",
    ),
    (
        "`environment: \"local\"`",
        "the current working directory",
    ),
    (
        "`readonly: true`",
        "a read-only agent whose `tools` line is `read`, `grep`, `find`, `ls`",
    ),
    (
        "`readonly: false`",
        "an agent with the full tool set, MCP tools included",
    ),
    (
        "`run_in_background: true`",
        "a `subagent` call, which returns when the child finishes",
    ),
    (
        "`resume`",
        "a fresh `subagent` with the earlier result pasted in",
    ),
    (
        "`file_attachments`",
        "the paths in the brief",
    ),
]

PATH_RULES = [
    (
        r"~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>\.jsonl",
        "~/.pi/agent/sessions/--<workspace-path>--/<timestamp>_<session-id>.jsonl",
    ),
    (
        r"~/.claude/projects/<slug>/\*\.jsonl",
        "~/.pi/agent/sessions/--<workspace-path>--/*.jsonl",
    ),
    (r"~/.claude/projects/<slug>", "~/.pi/agent/sessions/--<workspace-path>--"),
    (r"~/\.cursor/projects/\*/agent-transcripts", "~/.pi/agent/sessions/*"),
    (r"~/\.cursor/projects/", "~/.pi/agent/sessions/"),
    (r"\.cursor/projects/", "~/.pi/agent/sessions/"),
    (r"~/.cursor/rules/pstack-models\.mdc", "~/.pi/agent/pstack-models.md"),
    (r"`pstack-models\.mdc`", "`pstack-models.md`"),
    (r"pstack-models\.mdc", "pstack-models.md"),
    (r"~/.cursor/skills/", "~/.pi/agent/skills/"),
    (r"\.cursor/skills/", ".pi/skills/"),
    (r"~/.cursor/plugins/", "~/.pi/agent/"),
    (r"\.cursor/worktrees/", ".pi/worktrees/"),
    (r"\.cursor/rules/", "~/.pi/agent/"),
    (r"\.cursor/", ".pi/"),
    (r"agent-transcripts/", "sessions/"),
]

BLOCK_RULES = [
    (
        """# Transcripts dir: ~/.cursor/projects/<slugified-repo-path>/agent-transcripts.
slug=$(printf '%s' "$main_wt" | sed 's#^/##; s#/#-#g')
transcripts="$HOME/.cursor/projects/$slug/agent-transcripts"
""",
        """# Sessions live at ~/.pi/agent/sessions/--<slugified-repo-path>--/*.jsonl.
# Pi writes plain JSONL, so the scan reads them directly.
slug=$(printf '%s' "$main_wt" | sed 's#^/##; s#[/\\\\:]#-#g')
sessions="$HOME/.pi/agent/sessions/--$slug--"
""",
    ),
    (
        """\tif [ -d "$transcripts" ]; then
\t\tf=$(rg -l -e "${wt}/" -e "${wt}\\\"" "$transcripts" 2>/dev/null \\
\t\t\t| xargs stat -f '%m %N' 2>/dev/null | sort -rn | head -1)
\t\tif [ -n "$f" ]; then last_ts=$(echo "$f" | awk '{print $1}')
\t\t\tlast=$(date -r "$last_ts" '+%Y-%m-%d' 2>/dev/null); fi
\tfi
""",
        """\tif [ -d "$sessions" ]; then
\t\tf=$(rg -l -e "${wt}/" -e "${wt}\\\"" "$sessions" 2>/dev/null \\
\t\t\t| xargs stat -f '%m %N' 2>/dev/null | sort -rn | head -1)
\t\tif [ -n "$f" ]; then last_ts=$(echo "$f" | awk '{print $1}')
\t\t\tlast=$(date -r "$last_ts" '+%Y-%m-%d' 2>/dev/null); fi
\tfi
""",
    ),
    (
        """---
description: pstack per-role model choices (overrides skill defaults)
alwaysApply: true
---
# pstack model configuration.""",
        """# pstack model configuration.""",
    ),
    (
        """# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.
# budget: large (xhigh)
feature, refactoring: grok-4.7-xhigh-fast
bug-fix: grok-4.7-xhigh-fast
perf-issue: grok-4.7-xhigh-fast
hillclimb: grok-4.7-xhigh-fast
judgment and prose: claude-opus-5-5-xhigh
hardest tasks: claude-opus-5-5-xhigh
how explorer: grok-4.7-xhigh-fast
how explainer: claude-opus-5-5-xhigh
why investigators: grok-4.7-xhigh-fast
why synthesizer: claude-opus-5-5-xhigh
reflect tooling: grok-4.7-xhigh-fast
reflect judgment, divergent, synthesizer: claude-opus-5-5-xhigh
arena runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
arena cross-judge pool: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
swarm workers: grok-4.7-xhigh-fast
architect runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast
interrogate reviewers: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast""",
        """# pstack model configuration. One line per role. Delete a line to fall back to the skill default.
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
interrogate reviewers: <strong judgment id>, <fast code id>""",
    ),
    (
        "**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). `unlimited`, `large`, `medium`, and `small` set the effort token of every real slug, panel entries included, to `max`, `xhigh`, `high`, or `medium`. The effort token is the last token, or the one before a trailing `fast`, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a detected slug, use the same family's detected slug with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `unlimited` turns `claude-opus-5-5-xhigh` into `claude-opus-5-5-max`. Grok slugs top out at `xhigh`, so under `unlimited` the fallback puts Grok at `xhigh` and keeps `grok-4.7-xhigh-fast` as it is. `large` keeps both defaults. `small` turns them into `claude-opus-5-5-medium` and `grok-4.7-medium-fast`.",
        "**(b) Apply it.** Build the working table from the role defaults. The defaults in this skill are pstack's portable Cursor slugs, not Pi model ids. On Pi, replace each with a detected id of the same tier: a fast, cheap model for code roles and the strongest judgment model for prose and judgment. Add a `:<thinking>` suffix when the role needs a level other than the model default, for example `anthropic/claude-opus-5-5:xhigh`. `inherit-parent` and `auto` do not change. If no detected id fits a role, mark it as needing a choice.",
    ),
    (
        "Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.",
        "Every real id written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real id is not available, stop and ask again.",
    ),
    (
        "Tell the user the rule was written and that it applies to new sessions. Re-running this skill updates it.",
        "Tell the user the file was written and that it applies to new sessions. Each role binds to an agent file: a role takes effect only when a file under `~/.pi/agent/agents/` names its model. Re-running this skill updates the file.",
    ),
    (
        "### 5. Write the rule",
        "### 5. Write the file",
    ),
    (
        "name the current budget when the rule records one. With no rule, say that `large` matches the skill defaults.",
        "name the current budget when the file records one. With no file, say that `large` matches the skill defaults.",
    ),
    (
        "marking any real slug not in the detected set as needing a choice",
        "marking any real id not in the detected set as needing a choice",
    ),
    (
        "(both mean: this role runs on the parent chat model, which is how Auto users stay on Auto)",
        "(both mean: this role runs on the parent chat model)",
    ),
    (
        """Whether `/tomato-mode` stays on depends on how the user starts it:

- Enter on `/tomato-mode` attaches the skill to one message. It fades as the chat moves on.
- Option+Enter on Mac or Alt+Enter on Windows, or Use as Mode from the skill entry, makes it a Custom Mode. It stays in context every turn until the user exits the mode, and it stays out of casual turns.
- Cursor's docs list Custom Modes in the Agents Window and the CLI. Elsewhere, start each new task with `/tomato-mode`.""",
        "`/skill:tomato-mode` attaches the skill to the current request. Pi has no mode that keeps it on, so start each new task with `/skill:tomato-mode`.",
    ),
    (
        'A message that asks for work, such as "use pstack to fix this bug", is not a help question. Read [`tomato-mode`](../tomato-mode/SKILL.md), do the work under it, and mention once that a Custom Mode keeps it on.',
        'A message that asks for work, such as "use pstack to fix this bug", is not a help question. Read [`tomato-mode`](../tomato-mode/SKILL.md), do the work under it, and mention once that starting each task with `/tomato-mode` keeps the style on.',
    ),
    (
        "pstack has no planning skill. Cursor's Plan Mode works alongside it.",
        "pstack has no planning skill. Pi's `/plan` command toggles read-only plan mode.",
    ),
    (
        'Without `/tomato-mode`, a phrase such as "babysit this pr" can start Cursor\'s own skill for the same job instead.',
        'Without `/tomato-mode`, a phrase such as "babysit this pr" does not start pstack\'s playbook.',
    ),
    (
        "- `/loop` and `/create-skill` are Cursor built-ins.",
        "- `/loop` is a Cursor built-in with no Pi equivalent. Pi has no built-in skill-authoring command.",
    ),
    (
        "| The mode stopped applying after a few turns | It was started with Enter. Start it as a Custom Mode, or start each task with `/tomato-mode`. |",
        "| The mode stopped applying after a few turns | Pi has no persistent mode. Start each task with `/tomato-mode`. |",
    ),
    (
        "| Parallel agents overwrote each other | Give each agent its own worktree, or run them as cloud agents, which each get their own machine. |",
        "| Parallel agents overwrote each other | Give each agent its own worktree. Pi has no cloud workers. |",
    ),
    (
        "| An overnight run moved but finished nothing | `/loop` needs a check that can pass or fail, not a duration. See [guide page 7](../../pstack/docs/guide/07-overnight.md). |",
        "| An overnight run moved but finished nothing | Pi has no `/loop`. Use an external scheduler and give it a check that can pass or fail. See [guide page 7](../../pstack/docs/guide/07-overnight.md). |",
    ),
    (
        "| Run parallel checks over slices, or race workers, as cloud agents | [`/swarm`](../swarm/SKILL.md) |",
        "| Run parallel checks over slices, or race workers, as subagents | [`/swarm`](../swarm/SKILL.md) |",
    ),
    (
        "Before spawning investigators, list the available MCPs from the Cursor environment. Use the available-tools map when present. Otherwise inspect the `mcps/` directory Cursor exposes for enabled MCP servers.",
        "Before spawning investigators, list the MCP tools visible in this session. Pi loads servers from `mcp.json` and exposes each server's tools by name, so classify by the tool names, descriptions, and resource descriptors.",
    ),
    (
        "Transcripts live at `~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>.jsonl`, where `<slug>` is the workspace path with the leading slash dropped and each \"/\" turned into \"-\" (so `/Users/you/proj` becomes `Users-you-proj`). Every line is one chat message.",
        "Transcripts live at `~/.pi/agent/sessions/--<workspace-path>--/<timestamp>_<session-id>.jsonl`, where the directory name drops the leading slash, replaces `/`, `\\`, and `:` with `-`, and wraps the result in `--` (so `/Users/you/proj` becomes `--Users-you-proj--`). The first line is a session header, and every later line is one entry.",
    ),
    (
        "2. Pick the wake mechanism using Cursor's `/loop` command (a built-in, not a pstack skill). An event to watch (CI, a merge, a ref advancing) gets a watcher subagent that wakes you on the event, with a long time-based heartbeat as fallback. No event gets a fixed-interval heartbeat sized to when the result is worth re-checking. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section.",
        "2. Pick the wake mechanism. Pi has no loop command, so an external scheduler starts a fresh Pi session with the predicate. An event to watch (CI, a merge, a ref advancing) gets a polling script or CI trigger that starts the session when the event fires, with a long time-based heartbeat as fallback. No event gets a fixed-interval external timer sized to when the result is worth re-checking. The watcher lives outside Pi; a `subagent` call cannot wake this chat.",
    ),
    (
        "- [ ] On the operator's go, arm the audit tick as `/loop 1h` with the tick prompt below. Never leave the cadence to memory.",
        "- [ ] On the operator's go, arm an external hourly scheduler with the tick prompt below. Never leave the cadence to memory.",
    ),
    (
        "On the operator's go, arm `/loop 1h` to audit until no delegated work is left, because long runs drift and agents stall silently.",
        "On the operator's go, arm an external hourly scheduler to audit until no delegated work is left, because long runs drift and agents stall silently.",
    ),
    (
        "Investigate the pixel delta. `/loop` per component until the diff is zero.",
        "Investigate the pixel delta. Repeat the check per component until the diff is zero.",
    ),
    (
        "give `/loop` that predicate.",
        "give the scheduler that predicate.",
    ),
    (
        "don't ask me before committing. /loop until done.",
        "don't ask me before committing. Repeat until done.",
    ),
    (
        "This playbook replaces Cursor's built-in babysit skill for these requests, so do not route there.",
        "This playbook owns these requests, so do not route them to a host's built-in babysit skill.",
    ),
    (
        "Cloud agents cannot read the local store, so their briefs inline what they need or point at repo paths.",
        "Every worker runs on this machine, so a brief can point at local paths or repo paths.",
    ),
    (
        "Probe read-only: the ledger, `units.tsv`, `gh`, pushed branches, the cloud agent's status in the Cursor dashboard.",
        "Probe read-only: the ledger, `units.tsv`, `gh`, pushed branches, and the worktree state.",
    ),
    (
        "After a Cursor restart: local agents are dead, cloud work is not. Re-read the standing orders and `units.tsv`, recompute the frontier, reattach cloud work by PR and branch rather than agent id, r",
        "After a Pi restart: every child is dead. Re-read the standing orders and `units.tsv`, recompute the frontier, and restart the work from its branch and PR, r",
    ),
    (
        "Drive a long or stubborn hunt with Cursor's `/loop` command.",
        "Drive a long or stubborn hunt with an external scheduler that starts a fresh session.",
    ),
    (
        "under `/loop` until it reports `COMPLETE`",
        "repeatedly until it reports `COMPLETE`",
    ),
    (
        "Run `drive` and `background` under `/loop` in dynamic mode.",
        "Run `drive` and `background` repeatedly in dynamic mode.",
    ),
    (
        "| An overnight run moved but finished nothing | `/loop` needs a check that can pass or fail, not a duration.",
        "| An overnight run moved but finished nothing | An external check needs a predicate that can pass or fail, not a duration.",
    ),
    (
        "This playbook replaces Cursor's built-in babysit skill for these requests, so do not route there even though its description matches the same words.",
        "This playbook owns these requests, so do not route them to a host's built-in babysit skill even when its description matches the same words.",
    ),
    (
        "One verifier per PR, each a Cursor cloud agent, runs the change",
        "One verifier per PR, each a subagent in its own worktree, runs the change",
    ),
    (
        "Each owner is a Cursor cloud agent that builds",
        "Each owner is a subagent in its own worktree that builds",
    ),
    (
        "When a worker must start from a non-default pushed branch, pass `cloud_base_branch`.",
        "When a worker must start from a non-default pushed branch, check it out in its worktree before it starts.",
    ),
    (
        "Each live lane runs on its own cloud VM at the PR head. Drive through `control-ui` or `control-cli` from `cursor-team-kit`.",
        "Each live lane runs in its own worktree at the PR head. Drive the real surface with the harness the project uses; the Cursor control skills are absent.",
    ),
    (
        "its spawn budget with the cloud default and the local exception list",
        "its spawn budget and worktree list",
    ),
    (
        "Verbatim paste is for cloud spawns and every resume.",
        "Verbatim paste is for every spawn.",
    ),
    (
        "Chain rebases run in cloud. A local rebase at this scale takes the laptop down.",
        "Chain rebases run in a dedicated worktree. They still compete for the laptop at this scale.",
    ),
]

SESSION_RULES = [
    (
        "under the active workspace's `sessions/` directory (the system prompt names the path. Do not glob across",
        "under `~/.pi/agent/sessions/--<workspace-path>--/` (do not glob across",
    ),
    (
        "under the active workspace's `sessions/` directory (the system prompt names this path).",
        "under `~/.pi/agent/sessions/--<workspace-path>--/`.",
    ),
    (
        "under the active workspace's `sessions/` directory (the system prompt names the path).",
        "under `~/.pi/agent/sessions/--<workspace-path>--/`.",
    ),
    (
        "Locate the active workspace's transcripts before fanning out. The system prompt names the workspace's `sessions/` directory. Use only that path.",
        "Locate this workspace's sessions before fanning out. Use `~/.pi/agent/sessions/--<workspace-path>--/`.",
    ),
    (
        "Reading local transcripts under `sessions/`.",
        "Reading local sessions under `~/.pi/agent/sessions/--<workspace-path>--/`.",
    ),
]

TAIL_RULES = [
    (
        "Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "Choose the agent whose `model` carries the role, per the Subagents section of the **tomato-mode** skill.",
    ),
    (
        "Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section.",
        "Choose the agent whose `model` carries the role, per the Subagents section.",
    ),
    (
        "spawn a subagent on a different model family from the one that did the work",
        "spawn an agent on a different model family from the one that did the work",
    ),
    (
        "Spawn parallel subagents on a fast, cheap model",
        "Spawn parallel agents whose `model` is a fast, cheap model",
    ),
    (
        "Delegate code-writing to a subagent using your configured feature model",
        "Delegate code-writing to an agent whose `model` is your configured feature model",
    ),
    (
        "Hand the change to a subagent using your configured hillclimb model",
        "Hand the change to an agent whose `model` is your configured hillclimb model",
    ),
    (
        "Delegate implementation to a subagent using your configured perf-issue model",
        "Delegate implementation to an agent whose `model` is your configured perf-issue model",
    ),
]

REFLECT_RULES = [
    (
        "Before fanning out, find this conversation's transcript in the `agent-transcripts/` directory the system prompt names. Do not glob across `~/.cursor/projects/*/`. That crosses workspace boundaries and reads private chats from unrelated projects.",
        "Before fanning out, find this conversation's session file under `~/.pi/agent/sessions/--<workspace-path>--/`. Do not scan another workspace's directory: each one may hold private chats.",
    ),
    (
        "ls -t <agent-transcripts>/*.jsonl <agent-transcripts>/*/*.jsonl <agent-transcripts>/*/subagents/*.jsonl 2>/dev/null | head -10",
        "ls -t ~/.pi/agent/sessions/--<workspace-path>--/*.jsonl 2>/dev/null | head -10",
    ),
    (
        "That covers the legacy flat (`<id>.jsonl`), current nested (`<id>/<id>.jsonl`), and subagent (`<parent>/subagents/<child>.jsonl`) layouts. For each candidate, read the first JSONL line. Take the file whose `message.content[0].text` contains the conversation's opening user prompt. If none matches, pass a tight digest of the session instead.",
        "The first line is a session header with `type: \"session\"`, followed by `message` entries. For each candidate, find the first `user` message and take the file whose text contains the conversation's opening prompt. The `subagent` tool runs each child with `--no-session`, so child turns are not in this file; the parent records each call and its final output. If none matches, pass a tight digest of the session instead.",
    ),
]

ROLE_RULES = [
    (
        "**Use `subagent_type: \"tomato-agent\"` for any subagent you spawn inside a playbook step** (code-writing delegates, ad-hoc helpers). The chat that receives `/tomato-mode` runs the playbook. Never spawn a `tomato-agent` to run the playbook itself. Routed workflow skills (`how`, `why`, `interrogate`, `reflect`, `swarm`) set their own `subagent_type` for diverse-model review. Respect what the skill prescribes, don't override to `tomato-agent`.",
        "**Use the `tomato-agent` agent for any subagent you spawn inside a playbook step** (code-writing delegates, ad-hoc helpers). The chat that receives `/skill:tomato-mode` runs the playbook. Never spawn a `tomato-agent` to run the playbook itself. Routed workflow skills (`how`, `why`, `interrogate`, `reflect`, `swarm`) name their own agents for diverse-model review. Respect what the skill prescribes, don't override to `tomato-agent`.",
    ),
    (
        "**Defaults for every `Task` call.** `run_in_background: true`, agent mode (readonly strips MCP), file pointers not inlined context, explicit model per role (configurable via `/setup-pstack`. Defaults `grok-4.7-xhigh-fast` for code, `claude-opus-5-5-xhigh` for prose and judgment). Code delegates tier by difficulty. The hardest changes (cross-cutting design, gnarly concurrency, subtle algorithms) go to your strongest judgment model (`claude-opus-5-5-xhigh`), whether the task needs judgment on vague intent or is a precisely specified sequence of steps to execute to the letter. Trivial mechanical edits go to your fast code model. Per-role lines in the `/setup-pstack` rule override these defaults and the model choices in the routed skills (`how`, `why`, `arena`, `swarm`, `architect`, `interrogate`, `reflect`). A role with no line keeps its default, and a role line of `inherit-parent` or `auto` runs that role on the parent chat model (omit Task `model`). Each code playbook's configured model comes from its line (`feature, refactoring`, `bug-fix`, `perf-issue`, or `hillclimb`), and the hardest changes read `hardest tasks`. Prose and judgment read `judgment and prose`.",
        "**Defaults for every `subagent` call.** One call per child, and the call returns when that child finishes. Agent mode with the full tool set, MCP tools included; a read-only role gets an agent whose `tools` line is `read`, `grep`, `find`, `ls`. File pointers, not inlined context. The model comes from the named agent's `model` field, so each role maps to an agent file (configurable via `/skill:setup-pstack`). The portable defaults are `grok-4.7-xhigh-fast` for code and `claude-opus-5-5-xhigh` for prose and judgment; `/skill:setup-pstack` maps them to Pi model ids. Code delegates tier by difficulty. The hardest changes (cross-cutting design, gnarly concurrency, subtle algorithms) go to your strongest judgment model (`claude-opus-5-5-xhigh`), whether the task needs judgment on vague intent or is a precisely specified sequence of steps to execute to the letter. Trivial mechanical edits go to your fast code model. Per-role lines in `~/.pi/agent/pstack-models.md` override these defaults and the model choices in the routed skills (`how`, `why`, `arena`, `swarm`, `architect`, `interrogate`, `reflect`). A role with no line keeps its default, and a role line of `inherit-parent` or `auto` selects an agent with no `model` field, so that role runs on the parent chat model. Each code playbook's configured model comes from its line (`feature, refactoring`, `bug-fix`, `perf-issue`, or `hillclimb`), and the hardest changes read `hardest tasks`. Prose and judgment read `judgment and prose`.",
    ),
    (
        "**Match the model to the job.** Before each spawn, start from the role's line or default and pick the reasoning level and speed the job needs. The `/setup-pstack` budget sets each role's starting level, xhigh by default. Raise it one step, up to max, for the hardest or subtlest work. Lower it one step for judgment and two or more steps for routine work. Use fast mode only when the job is urgent, meaning CI or trunk is red or a person is blocked on the result right now. Otherwise use standard speed, the same slug without `-fast`. Verification is the exception and stays on the `swarm workers` model and speed (`grok-4.7-xhigh-fast` by default). Change only the effort level and whether the slug is fast, and keep the family the role names, so a diverse panel stays diverse. If the family has no slug at that level and speed, use its nearest slug. A role on `auto` or `inherit-parent` stays on the parent model. If the Task tool rejects the adjusted slug, do not try another adjusted slug. Use the role's line or default and say so.",
        "**Match the model to the job.** Before each spawn, read the role's line or default and pick the agent whose `model` carries it. The `/skill:setup-pstack` budget sets each role's value. The `subagent` tool takes no model or reasoning-level parameter: an agent with a `model` field runs on that model, and an agent without one inherits this session's model and thinking level. Choose the agent, not a slug in the brief. If no agent file carries the role's model, say so and use the closest available agent.",
    ),
    (
        "**Fresh subagents by default.** Give new work to a fresh subagent with consolidated scope, meaning the original brief, every later directive, and the prior agent's report and branch. This holds for a fix round, a follow-up, a retry, and the next queue item. Resume, message, or queue a follow-up on an existing subagent only when the new work strictly needs state that lives in that agent and is costly to move: its local checkout, its uncommitted changes, or a process it still runs, such as a dev server, a simulator, or a babysit watcher. A stop or hold order to a running agent is not reuse. A role such as a PR owner outlives its agent. Once that agent returns, a fresh agent takes the role's next round. Interrupt-chained resumes silently drop directives, so fire a fresh subagent with consolidated scope rather than trusting a \"done\" summary.",
        "**Fresh subagents by default.** Give new work to a fresh subagent with consolidated scope, meaning the original brief, every later directive, and the prior agent's report and branch. This holds for a fix round, a follow-up, a retry, and the next queue item. The `subagent` tool has no resume or message operation, and a call returns only the child's final output. Carry state forward by pasting the earlier result, the paths, the branch, and the remaining work into a fresh call. A role such as a PR owner outlives its agent. Once that agent returns, a fresh agent takes the role's next round.",
    ),
    (
        "Every spawn is a Task subagent with `subagent_type: generalPurpose` and `readonly: true`. Explorers use the `how explorer` line in the `pstack-models.mdc` rule (default `grok-4.7-xhigh-fast`), and every explainer uses the `how explainer` line (default `claude-opus-5-5-xhigh`). Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "Every spawn is a `subagent` call on a read-only agent whose `tools` line is `read`, `grep`, `find`, `ls`. Explorers use the `how explorer` line in `~/.pi/agent/pstack-models.md` (default `grok-4.7-xhigh-fast`), and every explainer uses the `how explainer` line (default `claude-opus-5-5-xhigh`). Choose the agent whose `model` is that line's value, or the default if the file or the line is missing. An `auto` or `inherit-parent` value means an agent with no `model` field, so it inherits this session's route. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent.",
    ),
    (
        "Each spawn below names a role line in the `pstack-models.mdc` rule and a default. Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "Each spawn below names a role line in `~/.pi/agent/pstack-models.md` and a default. Choose the agent whose `model` is that line's value, or the default if the file or the line is missing. An `auto` or `inherit-parent` value means an agent with no `model` field, so it inherits this session's route. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent.",
    ),
    (
        "Every spawn is `generalPurpose` with `readonly: false` (agent mode). **Do not use readonly/Ask mode.** It strips MCP access, which disables the MCP-backed investigators and the synthesizer's citation spot-checks. Investigators still shouldn't write anything.",
        "Every spawn is a `subagent` call on an agent with the full tool set, MCP tools included. **Do not use a read-only agent.** A `tools` allowlist that omits MCP tools disables the MCP-backed investigators and the synthesizer's citation spot-checks. Investigators still shouldn't write anything.",
    ),
    (
        "Spawn one investigator per category that has a matching MCP, all in a single message so they run concurrently, each owning exactly one tool or MCP. Don't ask one agent to cover multiple MCPs. `model`: the `why investigators` line, default `grok-4.7-xhigh-fast`.",
        "Spawn one investigator per category that has a matching MCP, all in a single message so they run concurrently, each owning exactly one tool or MCP. Don't ask one agent to cover multiple MCPs. Use an agent whose `model` is the `why investigators` line, default `grok-4.7-xhigh-fast`.",
    ),
    (
        "Spawn one synthesizer. `model`: the `why synthesizer` line, default `claude-opus-5-5-xhigh`. It gets:",
        "Spawn one synthesizer on an agent whose `model` is the `why synthesizer` line, default `claude-opus-5-5-xhigh`. It gets:",
    ),
    (
        "4. Pick the worker model from the `swarm workers` line in `~/.cursor/rules/pstack-models.mdc`. If the rule or that line is missing, use `grok-4.7-xhigh-fast`. For `auto` or `inherit-parent`, omit `model` so the workers run on the parent model. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. For a model race, name each arm's model up front. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "4. Pick the worker agent from the `swarm workers` line in `~/.pi/agent/pstack-models.md`. If the file or that line is missing, use `grok-4.7-xhigh-fast`. An `auto` or `inherit-parent` value means an agent with no `model` field, so the workers run on the parent model. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent. For a model race, name each arm's agent and model up front.",
    ),
    (
        "Spawn all N workers in one message with `subagent_type: generalPurpose`, `environment: \"cloud\"`, `run_in_background: true`, and the step 4 model, left unset for `auto` or `inherit-parent`. Use `environment: \"local\"` only when the worker needs access to something on the user's computer.",
        "Spawn all N workers in one message, one `subagent` call per worker, each call returning when that worker finishes. Run each in a `git worktree` named in the brief, and use the step 4 agent. Use the current working directory only when the worker needs access to something on the user's computer.",
    ),
    (
        "3. Pick the runners. Use the `arena runners` line in `~/.cursor/rules/pstack-models.mdc`. If the rule or that line is missing, default to one each on `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. An `auto` or `inherit-parent` entry in this line or the cross-judge line means the parent model, so omit `model` for it. If the Task tool rejects a configured entry, run that seat on its family's default and say so. Families go by prefix: `claude-*`, and `grok-*` with `cursor-grok-*` and `composer-*`. A refused `composer-*` entry runs on `grok-4.7-xhigh-fast`. With no family match, use `claude-opus-5-5-xhigh`. If it rejects a default, use the closest valid slug of the same family from its error message. Spawn more runners when the arena covers multiple design directions. Use the same model N times when the work is generation-bound rather than judgment-sensitive. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "3. Pick the runners. Use the `arena runners` line in `~/.pi/agent/pstack-models.md`. If the file or that line is missing, default to one each on `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. An `auto` or `inherit-parent` entry in this line or the cross-judge line means an agent with no `model` field, so it runs on the parent model. The `subagent` tool takes no `model` parameter: choose an agent whose `model` is the configured entry. If no agent file carries a configured entry, run that seat on its family's default and say so. Families go by prefix: `claude-*`, and `grok-*` with `cursor-grok-*` and `composer-*`. A `composer-*` entry with no agent runs on `grok-4.7-xhigh-fast`. With no family match, use `claude-opus-5-5-xhigh`. When no agent carries a default, use the closest available model from `pi --list-models` and say so. Spawn more runners when the arena covers multiple design directions. Use the same model N times when the work is generation-bound rather than judgment-sensitive.",
    ),
    (
        "Spawn all N subagents in one message with `run_in_background: true`, each with the task, the path to the shared grounding, its own output path, and instructions to produce the artifact and a short rationale naming the alternatives it considered and what it rejected.",
        "Spawn all N subagents in one message, one `subagent` call per candidate, each call returning when that candidate finishes. Give each the task, the path to the shared grounding, its own output path, and instructions to produce the artifact and a short rationale naming the alternatives it considered and what it rejected.",
    ),
    (
        "After all Phase B candidates complete, choose one model from the `arena cross-judge pool` line in `~/.cursor/rules/pstack-models.mdc`. If the rule or that line is missing, choose from `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. Prefer a different model family from the parent's. Spawn one readonly judge subagent on that model.",
        "After all Phase B candidates complete, choose one model from the `arena cross-judge pool` line in `~/.pi/agent/pstack-models.md`. If the file or that line is missing, choose from `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. Prefer a different model family from the parent's. Spawn one judge on a read-only agent whose `model` carries that choice.",
    ),
    (
        "Take the runners from the `architect runners` line in the `pstack-models.mdc` rule, in place of the `arena runners` line. If the rule or that line is missing, use `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. Alias and rejected entries follow the runner rules in the **arena** skill's Phase A.",
        "Take the runners from the `architect runners` line in `~/.pi/agent/pstack-models.md`, in place of the `arena runners` line. If the file or that line is missing, use `claude-opus-5-5-xhigh` and `grok-4.7-xhigh-fast`. Alias and missing-agent entries follow the runner rules in the **arena** skill's Phase A.",
    ),
    (
        "Launch all reviewers in a single message with the Task tool, one per entry on the `interrogate reviewers` line in `~/.cursor/rules/pstack-models.mdc`, labeled Reviewer A, B, and so on to match the entry count. If the rule or that line is missing, use the table defaults.",
        "Launch all reviewers in a single message with the `subagent` tool, one per entry on the `interrogate reviewers` line in `~/.pi/agent/pstack-models.md`, labeled Reviewer A, B, and so on to match the entry count. If the file or that line is missing, use the table defaults.",
    ),
    (
        "Each reviewer gets `subagent_type: generalPurpose`, `readonly: true`, and `model` set to its configured entry, or its table default when there is no configured line. Omit `model` for an `auto` or `inherit-parent` entry, so that reviewer runs on the parent model.",
        "Each reviewer gets a `subagent` call on a read-only agent whose `tools` line is `read`, `grep`, `find`, `ls`, and whose `model` is the configured entry or the table default when there is no configured line. An `auto` or `inherit-parent` entry means an agent with no `model` field, so that reviewer runs on the parent model.",
    ),
    (
        "If the Task tool rejects a configured entry, run that reviewer on its family's table default and say so. Families go by prefix: `claude-*`, and `grok-*` with `cursor-grok-*` and `composer-*`. A refused `composer-*` entry runs on Reviewer B's default. With no family match, use Reviewer A's default. If it rejects a table default, spawn with the closest equivalent from the valid slugs in its error message (prefer the same family and reasoning tier), and open a separate PR to update the default table. Do not block the review on the slug issue. Never treat an alias entry as a rejected slug or apply either fallback to it.",
        "If no agent file carries a configured entry, run that reviewer on its family's table default and say so. Families go by prefix: `claude-*`, and `grok-*` with `cursor-grok-*` and `composer-*`. A `composer-*` entry with no agent runs on Reviewer B's default. With no family match, use Reviewer A's default. If no agent carries a table default, spawn the closest available model from `pi --list-models` (prefer the same family and tier), and open a separate PR to update the default table. Do not block the review on the model issue. Never treat an alias entry as a missing agent or apply either fallback to it.",
    ),
    (
        "One message, three `Task` calls, `subagent_type: generalPurpose`, agent mode (`readonly: false`). Reviewers need MCP access to look up the tickets, chat threads, and observability traces the transcript references, and readonly strips MCPs.",
        "One message, three `subagent` calls, each on an agent with the full tool set, MCP tools included. Reviewers need MCP access to look up the tickets, chat threads, and observability traces the transcript references, and a `tools` allowlist that omits MCP tools removes that access.",
    ),
    (
        "Each reviewer and the synthesizer name a role line in the `pstack-models.mdc` rule and a default. Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the Task tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.",
        "Each reviewer and the synthesizer name a role line in `~/.pi/agent/pstack-models.md` and a default. Choose the agent whose `model` is that line's value, or the default if the file or the line is missing. An `auto` or `inherit-parent` value means an agent with no `model` field, so it inherits this session's route. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent.",
    ),
    (
        "One `Task` call, `subagent_type: generalPurpose`, `model` from the `reflect judgment, divergent, synthesizer` line (default `claude-opus-5-5-xhigh`), agent mode (`readonly: false`). It spot-verifies citations through MCP, and readonly strips MCPs.",
        "One `subagent` call on an agent whose `model` matches the `reflect judgment, divergent, synthesizer` line (default `claude-opus-5-5-xhigh`), with the full tool set, MCP tools included. It spot-verifies citations through MCP, and a read-only agent cannot.",
    ),
    (
        "1. Spawn `Task` with `subagent_type: \"comment-sicko\"`. Pass the scope. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill. Do not restate its rules.",
        "1. Spawn `subagent` with `comment-sicko`'s instructions in the brief, or with the `comment-sicko` agent when `~/.pi/agent/agents/comment-sicko.md` exists. Pass the scope. The `subagent` tool takes no model or reasoning-level parameter: the agent file carries the model. Do not restate its rules.",
    ),
    (
        "3. Explore in subagents with `subagent_type: \"tomato-agent\"` and an explicit model per the Subagents section (the **guard-the-context-window** principle skill). Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section. Each returns file pointers, conventions, test commands, and entry points. No inlined dumps.",
        "3. Explore in subagents with agent `tomato-agent` and a role model per the Subagents section (the **guard-the-context-window** principle skill). The `subagent` tool takes no model parameter: the agent file carries it. Each returns file pointers, conventions, test commands, and entry points. No inlined dumps.",
    ),
    (
        "Write `~/.cursor/rules/pstack-models.mdc`, an always-applied rule that sets pstack's model per role.",
        "Write `~/.pi/agent/pstack-models.md`, the role file that sets pstack's model per role. Pi loads no rules directory, so read it when a skill names a role.",
    ),
    (
        "Enumerate the model slugs you can pass to a `Task` subagent in this session. That is the dependable source. If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness. If you cannot detect any, ask the user to paste the slugs they have access to. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.",
        "Enumerate the model ids available to an agent file in this session with `pi --list-models`. That is the dependable source. If the command fails, ask the user to paste the ids they have access to. Never write a real id you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected ids.",
    ),
    (
        "The default role-to-model mapping is the rule shape shown in step 5 below.",
        "The default role-to-model mapping is the file shape shown in step 5 below.",
    ),
    (
        "Write `~/.cursor/rules/pstack-models.mdc` with `alwaysApply: true`, a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels tomato-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:",
        "Write `~/.pi/agent/pstack-models.md` with a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels tomato-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:",
    ),
    (
        "# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.",
        "# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (an agent with no `model` field). Alias entries in a panel list still count toward its fan-out.",
    ),
    (
        "Agents are spawned, resumed, and drained only through the Task tool.",
        "Agents are spawned and drained only through the `subagent` tool, and each call blocks until its child returns, so plan a rolling window of calls.",
    ),
    (
        "(nesting works to depth 3, and a nested spawn has the full Task schema including `environment`)",
        "(a child can spawn its own subagents, and each call blocks until the child returns)",
    ),
    (
        "pstack is built for Cursor. Its skills use the Agent Skills format, so other tools can read them. But most workflow skills, including `/tomato-mode`, `/how`, `/why`, and `/teach`, spawn Cursor subagents with per-role models, and Custom Modes and `/loop` are Cursor features, so those parts may not work there.",
        "pstack runs under Pi and Cursor. Its skills use the Agent Skills format. Pi skills live under `~/.pi/agent/skills`, are invoked as `/skill:<name>`, and use named agents for per-role models. Custom Modes and `/loop` are Cursor features with no Pi equivalent.",
    ),
    (
        "1. Use the **create-skill** skill (Cursor's built-in for authoring SKILL.md files).",
        "1. Follow this playbook's draft / test / iterate loop.",
    ),
    (
        "hand to Cursor's built-in `create-skill` skill and run its draft / test / iterate loop.",
        "hand to the **authoring-a-skill** playbook and run its draft / test / iterate loop.",
    ),
    (
        "hand to `create-skill` and run its description-optimization loop.",
        "hand to the **authoring-a-skill** playbook and run its description-optimization loop.",
    ),
    (
        "hand creation to `create-skill`.",
        "hand creation to the **authoring-a-skill** playbook.",
    ),
    (
        "Link [Cursor's skills docs](https://cursor.com/docs/skills) when this comes up. Mid-chat, \"new task\" makes the mode match a fresh playbook. `/tomato-mode` already uses `tomato-agent` for the subagents its playbook steps spawn. To get the same style from a subagent of your own, spawn it with `subagent_type: \"tomato-agent\"`.",
        "Link Pi's skills docs when this comes up. Mid-chat, \"new task\" starts a fresh playbook. `/skill:tomato-mode` already uses `tomato-agent` for the subagents its playbook steps spawn. To get the same style from a subagent of your own, spawn it with agent `tomato-agent`, or paste `~/.agents/pstack/agents/tomato-agent.md` into the brief.",
    ),
    (
        "Any prose surface, your reply to the user included → the **unslop** skill. Write the reply per **Writing the reply**. Agent-facing prose also follows the **create-skill** skill (Cursor's built-in for authoring SKILL.md files).",
        "Any prose surface, your reply to the user included → the **unslop** skill. Write the reply per **Writing the reply**. Agent-facing prose also follows the **authoring-a-skill** playbook.",
    ),
    (
        "not Cursor's built-in babysit skill, whose description matches the same words",
        "not a host's built-in babysit skill, whose description matches the same words",
    ),
    (
        "a Cursor restart",
        "a Pi restart",
    ),
    (
        "This skill orchestrates three others: an inline mining pass (see step 1), Cursor's built-in `create-skill` (authoring), and the **unslop** skill (prose discipline).",
        "This skill orchestrates three parts: an inline mining pass (see step 1), the **authoring-a-skill** playbook (authoring), and the **unslop** skill (prose discipline).",
    ),
    (
        "Use Cursor's built-in `create-skill` skill to author the skill.",
        "Use the **authoring-a-skill** playbook to author the skill.",
    ),
    (
        "Frontmatter formatting: follow `create-skill`'s YAML rules.",
        "Frontmatter formatting: follow the **authoring-a-skill** playbook's YAML rules.",
    ),
    (
        "Apply the **unslop** skill and `create-skill`'s writing guidelines to every line.",
        "Apply the **unslop** skill and the **authoring-a-skill** playbook's writing guidelines to every line.",
    ),
    (
        "A `create-skill`-style test/iterate benchmark loop isn't useful here.",
        "A drafting benchmark loop isn't useful here.",
    ),
    (
        "`create-skill` alone, no mining required.",
        "the **authoring-a-skill** playbook alone, no mining required.",
    ),
]

ADAPTER_FROM = (
    "This local port runs pstack under Claude Code. Read "
    "[the Claude Code adapter](../../pstack/docs/harness/claude-code.md) once per session "
    "before you follow this skill: it maps every Cursor name in pstack skills to its "
    "Claude Code equivalent."
)
ADAPTER_TO = (
    "This copy is generated for Pi and already uses Pi tool names. Read "
    "[the Pi adapter](~/.agents/pstack/docs/harness/pi.md) once per session for the rows "
    "a generated tree cannot change: subagent capability, isolation, model roles, and "
    "session transcripts."
)

CODE_EXT = (".md", ".mjs", ".ts", ".json", ".sh", ".lock", ".py")

SKILL_NAMES = sorted(
    name
    for name in os.listdir(SOURCE)
    if os.path.isdir(os.path.join(SOURCE, name))
)
COMMAND_RE = re.compile(
    r"(?<![\w./-])/(" + "|".join(re.escape(name) for name in SKILL_NAMES) + r")(?![\w-])"
)


def rewrite_span(match):
    inner = match.group(1)
    return "`" + SPAN.get(inner, inner) + "`"


def transform(text):
    text = text.replace(ADAPTER_FROM, ADAPTER_TO)
    text = text.replace("](../../pstack/", "](../../../../")
    for before, after in BLOCK_RULES:
        text = text.replace(before, after)
    for before, after in REFLECT_RULES:
        text = text.replace(before, after)
    for before, after in ROLE_RULES:
        text = text.replace(before, after)
    text = text.replace("create-skill", "authoring-a-skill")
    for literal, replacement in FIELD_RULES:
        text = text.replace(literal, replacement)
    text = re.sub(r"`([A-Za-z][A-Za-z0-9_]*)`", rewrite_span, text)
    for pattern, replacement in BARE:
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in PATH_RULES:
        text = re.sub(pattern, replacement, text)
    for before, after in SESSION_RULES:
        text = text.replace(before, after)
    for before, after in TAIL_RULES:
        text = text.replace(before, after)
    for pattern, replacement in (
        ("/principle-<name>", "/skill:principle-<name>"),
        ("/verify-<app>", "/skill:verify-<app>"),
    ):
        text = text.replace(pattern, replacement)
    text = COMMAND_RE.sub(r"/skill:\1", text)
    return text


def walk(base):
    for dirpath, _, names in os.walk(base):
        for name in sorted(names):
            if name == ".DS_Store":
                continue
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, base), full


def build():
    files = {}
    for rel, full in walk(SOURCE):
        top = rel.split(os.sep, 1)[0]
        if top in LOCAL_ONLY:
            continue
        data = open(full, "rb").read()
        if rel.endswith(CODE_EXT):
            try:
                data = transform(data.decode("utf-8")).encode("utf-8")
            except UnicodeDecodeError:
                pass
        files[rel] = (data, os.stat(full).st_mode & 0o111)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = build()
    if args.check:
        on_disk = {}
        if os.path.isdir(OUT):
            on_disk = {rel: open(full, "rb").read() for rel, full in walk(OUT)}
        drifted = sorted(
            p for p in set(files) | set(on_disk)
            if p not in files or p not in on_disk or files[p][0] != on_disk[p]
        )
        for path in drifted:
            print(f"generated/pi/skills/{path}")
        print(f"{len(drifted)} file(s) drifted of {len(files)}.")
        return 1 if drifted else 0

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for rel, (data, mode) in files.items():
        target = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(target) or OUT, exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)
        os.chmod(target, 0o755 if mode else 0o644)
    print(f"{len(files)} file(s) written to {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
