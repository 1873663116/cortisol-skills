---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
disable-model-invocation: true
---

# Reflect

This copy is generated for Pi and already uses Pi tool names. Read [the Pi adapter](~/.agents/pstack/docs/harness/pi.md) once per session for the rows a generated tree cannot change: subagent capability, isolation, model roles, and session transcripts.

Mine the current conversation for durable learnings, then route them into skill edits.

Invoke when the user says "reflect" or "/skill:reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## 1. Locate the active transcript

Before fanning out, find this conversation's session file under `~/.pi/agent/sessions/--<workspace-path>--/`. Do not scan another workspace's directory: each one may hold private chats.

```bash
ls -t ~/.pi/agent/sessions/--<workspace-path>--/*.jsonl 2>/dev/null | head -10
```

The first line is a session header with `type: "session"`, followed by `message` entries. For each candidate, find the first `user` message and take the file whose text contains the conversation's opening prompt. The `subagent` tool runs each child with `--no-session`, so child turns are not in this file; the parent records each call and its final output. If none matches, pass a tight digest of the session instead.

## 2. Spawn three reviewers in parallel

One message, three `subagent` calls, each on an agent with the full tool set, MCP tools included. Reviewers need MCP access to look up the tickets, chat threads, and observability traces the transcript references, and a `tools` allowlist that omits MCP tools removes that access.

Each reviewer and the synthesizer name a role line in `~/.pi/agent/pstack-models.md` and a default. Choose the agent whose `model` is that line's value, or the default if the file or the line is missing. An `auto` or `inherit-parent` value means an agent with no `model` field, so it inherits this session's route. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent.

| Lens | Role line | Default `model` | Prompt template |
|---|---|---|---|
| Judgment | `reflect judgment, divergent, synthesizer` | `claude-opus-5-5-xhigh` | `references/judgment-reviewer.md` |
| Tooling | `reflect tooling` | `grok-4.7-xhigh-fast` | `references/tooling-reviewer.md` |
| Divergent | `reflect judgment, divergent, synthesizer` | `claude-opus-5-5-xhigh` | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in the `subagent` response body.

## 3. Synthesize

One `subagent` call on an agent whose `model` matches the `reflect judgment, divergent, synthesizer` line (default `claude-opus-5-5-xhigh`), with the full tool set, MCP tools included. It spot-verifies citations through MCP, and a read-only agent cannot. Pass `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. It returns an Accepted / Rejected / Backlog list.

## 4. Structural enforcement check

Move any Accepted item that a lint rule, script, metadata flag, or runtime check would enforce more reliably to Backlog. See the **encode-lessons-in-structure** principle skill.

## 5. Apply

Present the synthesizer's full Accepted / Rejected / Backlog output and wait for explicit approval before applying any Accepted edit. The user picks the subset and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

File each Backlog item to your team's devex or backlog tracker without waiting. Only the Accepted list waits for approval.

Follow each approved row's Routing exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): the parent does it directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): hand to the **authoring-a-skill** playbook and run its draft / test / iterate loop.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): hand to the **authoring-a-skill** playbook and run its description-optimization loop.
- `new skill via authoring-a-skill: <kebab-name>`: hand creation to the **authoring-a-skill** playbook. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done.

## 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
