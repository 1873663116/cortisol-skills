# pstack in DeepSeek Harness

This tree is generated. `scripts/generate-deepseek.py` reads the pstack skills and rewrites the tool names, field names, and paths that DeepSeek Harness spells differently. Read this file once per session for the four rows a generated tree cannot change.

DSH routes to this tree by root rank. It scans `~/.dsh/skills` at rank 400 and `~/.agents/skills` at rank 500, and within one layer the lower rank wins a duplicate name. So this tree lives at `~/.dsh/skills` and the Claude Code tree stays at `~/.agents/skills`, and each host loads its own copy without either one knowing the other exists.

## Tools

The generated tree already uses these names. This table is here so you can check a skill that predates the generator.

| Skill says | DSH tool |
| --- | --- |
| `subagent` | `subagent`, which starts a child and returns at once |
| `subagent_fork` | A child seeded with this conversation's completed turns |
| `ask_user_question` | `ask_user_question` |
| `todo_write` | `todo_write` |
| `read`, `write`, `edit` | Same names, lower case |
| `grep`, `glob` | Same names, lower case |
| `bash` | Same |
| `skill` | `skill`, which loads a skill body by exact name |

A skill marked `disable-model-invocation: true` is absent from the catalog and refuses the `skill` tool. Reach it by typing `/name`, which injects the body into the step. That is the same rule Claude Code and Cursor use, and it is why `/tomato-mode` works but asking the model to "use tomato mode" does not.

## Subagents

`subagent` takes `prompt`, `description`, `cwd`, and, when the session policy allows it, `provider`, `model`, and `reasoning_effort`. It does not take a type, a readonly flag, or an environment flag. Three Cursor habits have no direct equivalent:

- **Named agent types.** There is no `agents/` loader, so `tomato-agent` and `comment-sicko` are not registered types. Their instructions live in `pstack/agents/`. Paste the relevant file into the delegation prompt, or read it first and summarize its constraints. A child given the file's content behaves the same as a child given its type.
- **Read-only reviewers.** Say `do not edit files` in the prompt, then check `git status` after the child settles. There is no flag that enforces it.
- **Cloud workers.** There is no cloud environment. A worker that needs a clean tree gets a `git worktree` path in its brief, created by the parent. `cwd` is the only location control the tool offers.

`subagent` returns a child id immediately and the runtime notifies you when it settles. To continue a child, use `send_message`. To resume work whose context is gone, start a new child and paste the earlier result.

`maxDepth` defaults to `1`, so a child cannot delegate further unless the host raises it.

## Models

`~/.claude/rules/` has no DSH equivalent, and DSH loads no rules directory. Role lines therefore live in `~/.agents/pstack-models.md`, which nothing loads automatically. Read it when a skill names a role, or keep the role values in the current conversation.

A role value is `<model> <effort>`, for example `deepseek/deepseek-v4.1-flash-fast high`. Pass the model as `provider` and `model` together, and the effort as `reasoning_effort`. Omit all three to inherit the parent route. Confirm what the session offers with `list_subagent_models` when it is visible, or read the configured providers in the profile.

`setup-pstack` writes the role file. Its detection step enumerates what the `subagent` tool accepts rather than guessing.

## Transcripts

DSH writes one compressed log per session: `~/.dsh/sessions/<slug>/session-<uuid>/session.v4.jsonl.zstd`. The slug is the workspace path with `/` and `.` replaced by `-`, prefixed by an extra `-`. Decompress with `zstd -dc` before reading, and read only the slug for this workspace.

`reflect` and `scripts/worktree-audit.sh` are already rewritten for this layout. A skill that still says `agent-transcripts/` predates the generator and needs the same treatment.

## Cursor-only features

DSH has no Cursor Automations, Bugbot, or cloud-agent dashboard. When a step needs one, write `Skipped in DeepSeek Harness: <step>. <reason>.` and continue. Do not stop or ask.

What DSH has instead of a Cursor automation loop is scheduled reminders: `schedule_create`, `schedule_list`, and `schedule_delete`. A playbook step that wants a repeated check over time uses those, and one that wants a persistent cross-turn goal uses `create_goal`.

## Regenerating

```bash
python3 pstack/scripts/generate-deepseek.py
python3 pstack/scripts/generate-deepseek.py --check
```

The generator reads `skills/`, which is the Claude Code tree, and writes `pstack/generated/deepseek/skills/`. That directory is what `~/.dsh/skills` points at. Edit the source skills, never the generated tree: `--check` reports drift and CI fails while it is non-empty.
