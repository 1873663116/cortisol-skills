# pstack on DeepSeek Harness

## The short answer

DeepSeek Harness (DSH) already loads every pstack skill, with no port at all. `dsh-skill-filesystem` scans `~/.agents/skills` at rank 500, and that is exactly where this repo keeps them. The catalog, the `skill` loader tool, the `/name` gesture, and live watching all work on the existing files.

This is observable in the current session, not just in the source. Of the 63 skills on disk, 58 carry `disable-model-invocation: true` and stay out of the catalog; the 5 that do not are `grilling`, `prompt-engineering`, `setup-pstack`, `subagent-dispatch`, and `writing-for-agents`, and those are exactly the 5 the session lists. `tomato-mode` is hidden, so it is reached by typing `/tomato-mode`, which is the same ergonomics Claude Code gives it.

What does not work is the text inside the skills. Every pstack skill speaks Cursor's vocabulary: `Task` instead of `subagent`, `AskQuestion` instead of `ask_user_question`, `environment: "cloud"` instead of an isolation mode, `.cursor/rules/pstack-models.mdc` instead of an instruction file, `agent-transcripts` instead of `~/.dsh/sessions`. The skills load and then instruct the model to call tools that do not exist.

So the work is not "port pstack to DSH". It is "give DSH the same small adapter pstack already gives Claude Code".

## What the two harnesses share

Upstream ships one generated Claude Code tree. The adapter for it is `pstack/docs/harness/claude-code.md`, 60 lines of tables. DSH matches Claude Code on more of those rows than it differs.

| Concern | Claude Code | DSH | Same? |
|---|---|---|---|
| Skill root | `~/.claude/skills` | `~/.agents/skills` at rank 500 | Different path, same layout |
| Skill format | `<name>/SKILL.md` with frontmatter | Same, `name` kebab-case and `description` required | Yes |
| Hide from model | `disable-model-invocation: true` | Same key, same behaviour | Yes |
| User invocation | `/name` | `/name`, whitespace-bounded token | Yes |
| Explicit load | `Skill` tool, refuses most | `skill` tool, refuses `disable-model-invocation` | Same refusal, different name |
| Catalog | injected list, name and description | injected `<available_skills>` user message, capped description | Yes |
| Subagent | `Agent`, `subagent_type` | `subagent` and `subagent_fork`, no `subagent_type` | No |
| Ask the user | `AskUserQuestion` | `ask_user_question` | Same shape, different name |
| Todo | `TodoWrite` | `todo_write` | Same shape, different name |
| Read, write, edit | `Read`, `Write`, `Edit` | `read`, `write`, `edit` | Same shape, different case |
| Search | `Grep`, `Glob` | `grep`, `glob` | Same shape, different case |
| Shell | `Bash` | `bash` | Same shape, different case |
| Always-on rules | `CLAUDE.md`, `~/.claude/rules/` | `AGENTS.md`, no rules directory | No |
| Transcripts | `~/.claude/projects/<slug>/*.jsonl` | `~/.dsh/sessions/<slug>/session-*/session.v4.jsonl.zstd` | No |
| Cloud workers | `isolation: "worktree"` | no isolation flag, `cwd` only | No |

Five rows are a rename. Three are a real gap.

## What is genuinely missing

**Subagent type.** DSH's `subagent` tool has no `subagent_type`. A child's capability comes from an `agent_preset`, which is a plugin composition declared in the profile, not a markdown file in a skill directory. There is no `agents/` loader: nothing scans `agents/*.md` the way skills are scanned. So `subagent_type: "tomato-agent"` cannot be reproduced by dropping a file in a folder. The portable substitute is to inline the agent's instructions into the delegation prompt, which is what `pstack/agents/*.md` already contains.

**Isolation.** `environment: "cloud"` and `environment: "local"` have no DSH counterpart. The `subagent` tool takes `cwd` and nothing else. A worker that needs a clean tree must get an explicit worktree path from the parent, or run `git worktree add` in its own brief.

**Model rules.** `~/.claude/rules/pstack-models.md` has no DSH equivalent, because DSH loads no rules directory. The nearest durable channel is `~/.agents/AGENTS.md`, which DSH reads as a user-global instruction file. Roles could live there as a small table, at the cost of adding to every session's prompt rather than only pstack's.

**Transcripts.** `reflect` and `worktree-audit.sh` read a JSONL tree. DSH writes `session.v4.jsonl.zstd`, one directory deeper and compressed. The reading logic does not transfer.

**Scheduled work.** Not a gap in pstack, but worth naming: DSH has `schedule_*` where Cursor had `/loop`, so `autopilot-full` can map that row cleanly instead of skipping it.

## Three ways to do it

### Option A: a DSH adapter document, next to the Claude Code one

Add `pstack/docs/harness/deepseek.md` with the tables above, written the way `claude-code.md` is. Change the adapter line the generator injects from a Claude Code pointer to one that says "read the adapter for your harness", and let the reader pick.

Cost: one new file, one generator rule, no change to any skill body. The skills stay one upstream copy.

Limit: the skills still say `Task` and `AskQuestion` inline. The adapter has to be read and applied in the reader's head, which is exactly how Claude Code works today. It works because the mapping is short and the model is good at it.

### Option B: a generated DSH tree, the way upstream does Claude Code

Extend `scripts/check-upstream.py` to also emit a second tree where the transforms rewrite Cursor names to DSH names in the text itself: `Task` to `subagent`, `AskQuestion` to `ask_user_question`, `generalPurpose` to a DSH preset or dropped, `.cursor/skills/` to `~/.agents/skills/`.

Cost: a second output tree, and the transform table grows from five rules to about twelve. Every new upstream skill must clear the same rules, and the rules must be kept honest as DSH adds tools.

Gain: the model reads DSH names directly, with no translation step, and a skill cannot silently drift back to Cursor names.

This is the option that matches how upstream already solved the same problem. Upstream did not write prose telling Claude Code to translate; it generates a tree.

### Option C: mirror the Claude Code tree and patch only the five gaps

Keep the generated tree as it is, and add a thin DSH layer that fixes only what actually breaks: subagent delegation, isolation, model rules, transcripts, and the ask/todo tool names. Everything else stays as Claude Code text, which DSH executes fine.

Cost: the smallest diff. It treats DSH as "Claude Code with different names", which is true for nine rows out of twelve.

Risk: the two harnesses drift. When DSH renames a tool, nothing notices until a skill fails.

## Recommendation

Option B, built on the rules already in `scripts/check-upstream.py`. The reason is not elegance. It is that this repo has just been through a merge where every file had been hand-edited, and the fix was to make the port mechanical and verify it by replay. A second hand-maintained adapter document repeats the mistake that made the last update expensive.

The work splits cleanly:

1. Add `HARNESS` transforms to `check-upstream.py`, so one upstream commit can emit both trees.
2. Generate `pstack/generated/deepseek/skills/`, point `~/.agents/skills` at it, and keep the Claude Code tree as a peer.
3. Verify by replay: from upstream bytes, the transform must reproduce every local file exactly. That check is already written and passing for the Claude Code tree.
4. Answer the gaps the transforms cannot close, in a `docs/harness/deepseek.md` that the generated skills point at: subagents, isolation, model roles, transcripts.

Step 4 is unavoidable in every option. Three of those four gaps are harness capability differences, not naming differences, and no transform can invent a capability.

## What I would confirm before starting

- Whether `agent_preset` can be extended from the profile so `tomato-agent` becomes a real preset. If yes, the subagent gap closes properly instead of degrading to an inlined prompt.
- Whether `~/.agents/AGENTS.md` is an acceptable home for the model-role table, or whether it should stay out of the global prompt.
- Whether the Claude Code tree should stay installed alongside the DSH tree, or be retired once DSH works.
