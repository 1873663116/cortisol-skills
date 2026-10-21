---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
disable-model-invocation: true
---

# Reflect

This copy is generated for DeepSeek Harness and already uses DSH tool names. Read [the DSH adapter](../../../../docs/harness/deepseek.md) once per session for the rows a generated tree cannot change: subagent capability, isolation, model roles, and session transcripts.

Mine the current conversation for durable learnings, then route them into skill edits.

Invoke when the user says "reflect" or "/reflect". Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## 1. Locate the active transcript

Before fanning out, find this conversation's session log under `~/.dsh/sessions/<slug>/`. Do not scan other slugs: each one is another workspace and may hold private chats.

```bash
ls -t ~/.dsh/sessions/*/session-*/session.v4.jsonl.zstd 2>/dev/null | head -10
```

Each log is zstd-compressed, so decompress before reading: `zstd -dc <log> | head -1`. Take the newest log whose opening user prompt matches. Subagent turns are recorded in the same log. If none matches, pass a tight digest of the session instead.

## 2. Spawn three reviewers in parallel

One message, three `subagent` calls, `subagent`, the full tool set, MCP servers included. Reviewers need MCP access to look up the tickets, chat threads, and observability traces the transcript references, and a reduced tool set would strip them.

Each reviewer and the synthesizer name a role line in the `AGENTS.md` rule and a default. Set `model` to that line's value, or to the default if the rule or the line is missing. Leave `model` unset when the value is `auto` or `inherit-parent`. If the `subagent` tool rejects a slug, use the default and say so. If it rejects the default, use the closest valid slug of the same family from its error message. Pick each subagent's reasoning level and fast or standard speed for the job, per the Subagents section of the **tomato-mode** skill.

| Lens | Role line | Default `model` | Prompt template |
|---|---|---|---|
| Judgment | `reflect judgment, divergent, synthesizer` | `command-code / gpt-6-luna` | `references/judgment-reviewer.md` |
| Tooling | `reflect tooling` | `command-code / deepseek/deepseek-v4.1-flash` | `references/tooling-reviewer.md` |
| Divergent | `reflect judgment, divergent, synthesizer` | `command-code / gpt-6-luna` | `references/divergent-reviewer.md` |

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in the `subagent` response body.

## 3. Synthesize

One `subagent` call, `subagent`, `model` from the `reflect judgment, divergent, synthesizer` line (default `command-code / gpt-6-luna`), the full tool set, MCP servers included. It spot-verifies citations through MCP, and a reduced tool set would strip them. Pass `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. It returns an Accepted / Rejected / Backlog list.

## 4. Structural enforcement check

Move any Accepted item that a lint rule, script, metadata flag, or runtime check would enforce more reliably to Backlog. See the **encode-lessons-in-structure** principle skill.

## 5. Apply

Present the synthesizer's full Accepted / Rejected / Backlog output and wait for explicit approval before applying any Accepted edit. The user picks the subset and may redirect routings. Skill changes affect every future agent in the org. Do not auto-apply.

File each Backlog item to your team's devex or backlog tracker without waiting. Only the Accepted list waits for approval.

Follow each approved row's Routing exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): the parent does it directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): hand to Cursor's built-in `create-skill` skill and run its draft / test / iterate loop.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): hand to `create-skill` and run its description-optimization loop.
- `new skill via create-skill: <kebab-name>`: hand creation to `create-skill`. Do not invent the shape ad hoc.

If your environment ships a SKILL.md validator, run it on every touched skill before declaring done.

## 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
