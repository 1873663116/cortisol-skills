# pstack in Pi

This tree is generated. `scripts/generate-pi.py` reads the pstack skills and rewrites the tool names, field names, paths, and host mechanics that Pi spells differently. Read this file once per session for the rows a generated tree cannot change.

Pi scans user skills at `~/.pi/agent/skills` and `~/.agents/skills`, and project skills at `.pi/skills` and any ancestor `.agents/skills`. The generated tree lives at `pstack/generated/pi/skills`; `~/.pi/agent/skills` points at it. On a duplicate name the first discovered skill wins, and the user skills directory is discovered before `~/.agents/skills`.

A skill marked `disable-model-invocation: true` stays out of the model catalog and refuses automatic selection. Invoke it as `/skill:<name>`. Text after the command is appended to the loaded instructions.

## Tools

The generated tree already uses these names. This table is here so you can check a skill that predates the generator.

| Skill says | Pi tool |
| --- | --- |
| `subagent` | `subagent`, from the example extension, with named agents |
| `ask_user_question`, `question` | `question`, from the example extension |
| `todo_write`, `todo` | `todo`, from the example extension |
| `read`, `write`, `edit` | Same names |
| `grep` | `grep` |
| `glob` | `find` |
| `bash` | `bash` |
| `skill` | No tool. Read the skill's `SKILL.md`, or run `/skill:<name>` |

Pi's core tools are `read`, `write`, `edit`, `bash`, `grep`, `find`, and `ls`. It has no `web_search`, `fetch`, schedule, goal, workflow, `present`, `list_agents`, `send_message`, or `subagent_fork` tool. The `subagent`, `todo`, and `question` tools load from example extensions and are absent until those extensions are installed.

Plan mode is the `/plan` command from the plan-mode extension. No `exit_plan_mode` tool exists.

## Subagents

The `subagent` tool comes from `examples/extensions/subagent` and starts a separate `pi` process for each child. It has three modes. Single is `{ agent, task }`. Parallel is `{ tasks: [{ agent, task }, ...] }`, up to 8 tasks and 4 at a time. Chain is `{ chain: [{ agent, task }, ...] }`, where `{previous}` in a task receives the prior output. The tool takes `agent`, `task`, `tasks`, `chain`, `agentScope`, `confirmProjectAgents`, and `cwd`.

A call returns when the child finishes and reports the child's final text. There is no background mode, no notification, no resume, and no message channel. A child runs with `--no-session`, so its transcript is not stored. The parent transcript records the tool call and its result.

Named agents live at `~/.pi/agent/agents/*.md`. Frontmatter carries `name`, `description`, optional `tools`, and optional `model`; the body is the child's system prompt. Project agents live at `.pi/agents/*.md` and load only when `agentScope` is `project` or `both`. The Pi tomato delegate lives at `pstack/agents/pi/tomato-agent.md`; copy it to `~/.pi/agent/agents/tomato-agent.md`. `pstack/agents/comment-sicko.md` is Cursor-flavored and has no Pi port yet. The generated tree contains no agent files.

Three Cursor habits map onto agent files and the brief.

- **Read-only reviewers.** Set `tools: read, grep, find, ls` in the agent frontmatter. The `subagent` call itself takes no readonly flag, so the allowlist is the only enforcement. A full-tool agent omits `tools`.
- **Cloud workers.** There is no cloud environment. A worker that needs a clean tree gets a `git worktree` path in its brief. Use `cwd` for a single task, or each `tasks` entry's `cwd` for parallel work.
- **Named agent types.** `tomato-agent` resolves only when its file exists under `~/.pi/agent/agents/`; `comment-sicko` has no Pi agent file yet. Without the file, paste the prompt into the brief.

A child is a normal Pi process and can spawn its own subagents when the extension is loaded. Each call blocks its caller until that child returns. Plan a rolling window of calls rather than a fan-out the parent cannot observe.

## Models and roles

Pi model ids have the form `<provider>/<model>`, as `pi --list-models` prints them. An agent's `model` field accepts one id and an optional `:thinking` suffix, for example `command-code/deepseek/deepseek-v4.1-flash` or `command-code/deepseek/deepseek-v4.1-flash:xhigh`. The suffix uses `off`, `minimal`, `low`, `medium`, `high`, `xhigh`, or `max`.

Role values live in `~/.pi/agent/pstack-models.md`. Pi loads no rules directory, so nothing reads that file automatically. Read it when a skill names a role, or keep the role values in the current session. Pi loads `~/.pi/agent/AGENTS.md` and project `AGENTS.md` as context files.

The `subagent` tool takes no `model` or reasoning-level parameter. A named agent with a `model` field runs on that model. An agent without one inherits the dispatching session's model and thinking level. To run a role on another model, create an agent file whose `model` carries it and name that agent in the call. Each role therefore maps to an agent file, not to a slug passed in the brief.

`/skill:setup-pstack` writes the role file. Its detection step runs `pi --list-models`. Role values must be Pi model ids. The defaults inside pstack skills are portable Cursor slugs, not Pi ids, and the setup skill replaces them with detected ids. Provider configuration lives in `~/.pi/agent/models.json`; the built-in catalog is refreshed with `pi update --models`.

## Transcripts

Pi writes one uncompressed JSONL file per session at `~/.pi/agent/sessions/--<path>--/<timestamp>_<session-id>.jsonl`. The directory name drops the leading slash, replaces `/`, `\`, and `:` with `-`, and wraps the result in `--`. The first line is a session header with `type: "session"`. Later lines are entries linked by `id` and `parentId`, which forms a tree.

Read only the directory for this workspace. Child subagent runs use `--no-session`, so their turns are absent. The parent records each `subagent` call and its final output.

`reflect` and `scripts/worktree-audit.sh` are already rewritten for this layout. A skill that still says `agent-transcripts/` predates the generator and needs the same treatment.

## Pi gaps

Pi has no Cursor Automations, Bugbot, cloud-agent dashboard, or Custom Mode dashboard. When a step needs one, write `Skipped in Pi: <step>. <reason>.` and continue. Do not stop or ask.

- **No background children.** A `subagent` call blocks. Playbooks written around spawn-and-continue, cloud fleets, or resuming idle agents do not map. Orchestrate assumes background workers and a durable coordinator fleet; run it only after rewriting that assumption.
- **No `/loop`.** Several playbooks arm `/loop` for a repeated audit. Use an external scheduler, cron, or CI trigger that starts a fresh Pi session with the same predicate. If no scheduler exists, skip the step and say so.
- **No cloud isolation.** Workers share this machine. One writer per worktree or branch remains mandatory.
- **No `send_message`, `subagent_fork`, or `list_agents`.** A child is one-shot. Paste the prior result into a fresh call.
- **No `create-skill` built-in.** The `authoring-a-skill` playbook inside `tomato-mode` owns skill authoring.
- **No `cursor-team-kit`.** `deslop`, `control-ui`, and `control-cli` are absent. Skip steps that require them.
- **`make-bot-ui` does not port.** Its routine creation, secret request, and webhook URL belong to Cursor Automations. Skip the skill in Pi.
- **MCP discovery differs.** Pi loads `mcp.json` servers and exposes their tools directly. There is no Cursor `mcps/` directory or available-tools map. The `why` skill is rewritten for direct tool discovery.
- **`todo` and `question` are extensions.** Install `examples/extensions/todo.ts` and `examples/extensions/question.ts`, or skip steps that need them.
- **No persistent tomato mode.** The generated tree defines no mode that stays on. `plugins/pi/tomato-reminder.ts` ships the mode commands. `/tomato-mode` loads `~/.pi/agent/skills/tomato-mode/SKILL.md` and adds one reminder line per user run while the mode is on; `/tomato-off` clears it. Install it with `ln -sfn ~/.agents/pstack/plugins/pi/tomato-reminder.ts ~/.pi/agent/extensions/tomato-reminder.ts` and run `/reload`.
- **Claude-tree skills stay visible.** Pi also scans `~/.agents/skills`. Five skills are model-visible across the two roots: `grilling`, `prompt-engineering`, `setup-pstack`, `subagent-dispatch`, and `writing-for-agents`. `setup-pstack` is ported here and wins the name collision. The other four remain in the Claude tree, unported, and load with Claude Code tool names. Porting them is follow-up work.

## Regenerating

```bash
python3 pstack/scripts/generate-pi.py
python3 pstack/scripts/generate-pi.py --check
```

The generator reads `skills/`, which is the Claude Code tree, and writes `pstack/generated/pi/skills/`. Edit the source skills, never the generated tree. `--check` reports drift and exits non-zero while it is non-empty.
