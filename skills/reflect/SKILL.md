---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
disable-model-invocation: true
---

# Reflect

Mine the current conversation for durable learnings, then route them into skill edits.

## When to invoke

- The user said "reflect" or "/reflect".
- A complex task (5+ tool calls) just landed cleanly and the recipe is worth keeping.
- The agent hit dead ends, found the working path, and the path generalizes.
- The user corrected the agent's approach mid-task.
- A non-trivial workflow emerged that isn't captured anywhere.

Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

The parent finds its own transcript file before fanning out. Claude Code stores workspace transcripts at `~/.claude/projects/<slug>/<uuid>.jsonl`. Use only the active workspace's `<slug>` directory. Do not glob across `~/.claude/projects/*/`. That crosses workspace boundaries and reads private chats from unrelated projects.

```bash
ls -t ~/.claude/projects/<slug>/*.jsonl 2>/dev/null | head -10
```

Derive `<slug>` from the absolute workspace path by encoding each `/` as `-`; Claude Code also encodes the leading `.` of a hidden path component as `-`. Keep the leading hyphen produced by the root slash. The confirmed directory for `/Users/xiongzhipeng/.agents` is `~/.claude/projects/-Users-xiongzhipeng--agents/`. The local layout has no `agent-transcripts/` level and no per-UUID directory.

For each candidate, scan from the start to the first entry whose `type` is `user`, then check that `message.content[0].text` contains the conversation's opening user prompt. Take the matching path. If no path resolves, write a tight digest of the session and pass that instead.

### 2. Spawn three reviewers in parallel

Read the **dispatch** skill. Call `delegate_to_agent` three times before collecting any result, using the agent types assigned to the roles below and the workspace's absolute path as `working_dir`. Reviewers may need MCP access for context lookups. `delegate_to_agent` cannot grant MCP access or enforce read-only operation, so confirm each selected agent type exposes the needed MCPs and put `Do not write or modify files` in every task. The parent applies edits.

| Lens | Dispatch role | Prompt template |
|---|---|---|
| Judgment | `Judgment` class | `references/judgment-reviewer.md` |
| Tooling | `reflect tooling` | `references/tooling-reviewer.md` |
| Divergent | `Judgment` class | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Keep each returned `task_id` and collect all three with `get_delegation_status`.

### 3. Synthesize

Read the **dispatch** skill and call `delegate_to_agent` using the agent type assigned to the `Judgment` class and the workspace's absolute path as `working_dir`. The synthesizer's quality check includes spot-verifying citations, so confirm that agent type exposes the needed MCPs. Put `Do not write or modify files` in the task. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. Keep the returned `task_id` and collect it with `get_delegation_status`. The synthesizer returns a structured Accepted / Rejected / Backlog list.

### 4. Structural enforcement check

Sanity-check the synthesizer's Accepted list. For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog. The synthesizer already applies this criterion; this is a final pass before edits land. See the **encode-lessons-in-structure** principle skill.

### 5. Apply

Before applying any Accepted edit, present the synthesizer's full Accepted/Rejected/Backlog output to the user and wait for explicit approval. The user picks which subset to apply and may redirect routings. Skill changes affect every future agent in the org; do not auto-apply.

Backlog items file to whatever devex / backlog tracker your team uses automatically. Those are tracker submissions, not skill edits. Only the Accepted list waits for approval.

For each approved Accepted item, follow the Routing field exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): parent does directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): apply the **writing-for-agents** skill and its skill mechanics.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): apply the **writing-for-agents** context-pointer rules to the description.
- `new skill via writing-for-agents: <kebab-name>`: apply the **writing-for-agents** skill and its skill mechanics. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done. Skip this step if it doesn't.

### 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
