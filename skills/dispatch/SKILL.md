---
name: dispatch
description: How to hand work to another local agent, which agent each role gets, and the recovery ladder when a result comes back wrong. Read before spawning any delegate or panel, and again when a delegate's result disappoints.
disable-model-invocation: true
---

# Dispatch

Every delegate goes through the codeg MCP tool `delegate_to_agent`, except where this file says otherwise: the sidekick lane for serial Claude work, and the direct-CLI route for per-run model or effort control. `delegate_to_agent` takes three arguments and nothing else:

- `agent_type`, one of `claude_code`, `codex`, `grok`, `cursor`, `open_code`.
- `task`, the whole prompt.
- `working_dir`, an absolute path.

## What `delegate_to_agent` forces

**No model or effort argument.** Both live in each CLI's own config; a per-run override goes through the direct-CLI route at the end of this file.

**Cold start.** The delegate sees nothing of your conversation. Pass the whole prompt as `task`, use an absolute `working_dir`, and point at files instead of inlining contents.

**No resume on this primitive.** One task, one result. A correction is a fresh dispatch carrying the consolidated scope. The sidekick lane below resumes, on a different primitive.

**No read-only mode.** When a delegate must not write, put `Do not write or modify files` in its task.

**You own the result.** Keep each task_id, collect with `get_delegation_status`, review the diff, and write your own summary.

## The sidekick lane

The lane exists only when you hold the Agent tool and `SendMessage`; a Claude Code orchestrator does. Holding neither, skip this section and dispatch cold.

The Agent tool spawns a Claude subagent, and `SendMessage` to the id it returns resumes that subagent with context intact, even after it has finished. Take the lane when Judgment work lands on Claude and the line holds serial, related tasks over one working set. Spawn once, put the orientation and the style line from Choosing the agent in the first task, then send each follow-up to the same id. A correction whose context is still live goes to the same id too. When direction changes, retire the id and start fresh with only the live direction.

A sidekick draws from the same five-hour `claude_code` window as the orchestrator. It adds no pool; what it saves is re-orientation and wall time. Parallel fan-outs stay on `delegate_to_agent`, where the load spreads across vendors instead of draining one window N times over.

## Roles map to a class, not to an agent

The class a role belongs to is a property of the work and does not change. Which agent serves that class is decided per dispatch, against the headroom you actually have.

| Class | Roles | What the work demands |
|---|---|---|
| Judgment | `why` synthesizer, `how` explainer, `reflect` judgment and divergent and synthesizer, the hardest changes, anything where the intent is vague | Reasoning quality; nothing else substitutes |
| Letter-precise | bug-fix, perf-issue, hillclimb, `reflect` tooling, sweeps, migrations, mechanical rewrites across many files | Following a specified sequence exactly, over a long run, without drifting |
| Bulk | `swarm` workers, `why` investigators, `how` explorer, trivial edits, feature, refactoring | Volume. Any capable agent will do, so the choice is a budget and latency call |
| Panel | `how` critics, `arena` runners, `architect` runners, `interrogate` reviewers | Disagreement. The point is four vendors, so seats must differ |

The `arena cross-judge` role sits outside the four classes: take any agent whose vendor differs from the parent's.

## Choosing the agent

Run `npx -y quota-axi` when the choice turns on headroom you have not actually seen. Any real fan-out qualifies, as does a pool you may have drained since you last looked. Then:

**Judgment and Letter-precise are capability constraints, budget does not move them.** Judgment goes to `claude_code`, letter-precise to `codex`. Serial Judgment from a Claude Code orchestrator takes the sidekick lane instead of repeated cold delegates. If the constrained agent has no headroom, the honest move is to say so and let the user decide, not to quietly substitute a weaker agent and hand back work that looks finished.

**Judgment and Letter-precise delegates carry the style.** Their task prompt starts with: `Read /Users/xiongzhipeng/.agents/skills/poteto-mode/SKILL.md in full before any work, and read the principle files it names as they become relevant to your task.` Upstream enforced this through a dedicated `poteto-agent` subagent type; a line in the prompt is the local equivalent, and skipping it is how delegate output drifts off style. Bulk delegates skip it, the read costs more than trivial work is worth. Panel reviewers skip it too, they run their own reviewer prompts.

**Bulk is a budget decision.** Read the numbers, then apply the reasoning below. Split it first by whether latency matters. A wide fan-out wants fast agents and the headroom that expires soonest. One long errand nobody is waiting on wants the opposite: the deepest pool, speed irrelevant. When `grok` and `cursor` are both out of headroom or otherwise unavailable, `open_code` is Bulk's standing fallback.

**Panels need four different vendors before they need the right four.** Substitute freely to fill a seat; a panel of three still works, a panel where two seats share a vendor does not.

## When a result comes back wrong

Cheapest fix first.

1. Suspect the task statement. Most drift is ambiguity. Rewrite it; a live sidekick gets the rewrite at its id, a codeg delegate gets a fresh dispatch of the same class.
2. Right direction but shallow means effort fell short, not ability. `codex`, `grok` and `cursor` re-run through the direct CLI with effort raised, same model. Claude gets the depth requirement sent to its sidekick, or a fresh Agent-tool spawn on a stronger model. `open_code` already runs at max effort; shallow output from it is a misclassification, go to 3.
3. Wrong direction, or the same failure surviving a clearer prompt, means the work was misclassified. The usual miss is Bulk that needed Judgment; reclassify and dispatch that class. If the class still looks right, take a second opinion: same prompt, different vendor, agreement is high-signal.

Failure after all three is information the user needs. Hand back what you tried; a fourth dispatch of the same work is waste.

## Quota economics

These are subscriptions, not metered calls, so unit price is the wrong thing to optimise. Four facts drive every choice.

**Headroom that expires soonest should be spent first.** Read every window against its own reset, never against another provider's percentage.

**Speed and endurance are different properties.** Measured on real tasks here, `grok` is the fast and still holds up on substantial work, and `codex` and `open_code` are both slow. Slow is only a defect when something waits on it.

**Two agents are deep enough not to ration: `codex` and `open_code`.** Both are slow, so spend them on long errands where nothing waits. Prefer `open_code` for reading, investigation and anything exploratory, and keep `codex` for work that has to follow a specification exactly, which is the thing it is uniquely good at and the reason to protect its pool.

**`claude_code` runs on one five-hour window** shared by your own session, every `claude_code` delegate, and every sidekick. Spending it on a delegate spends it on yourself, which is why volume goes to other vendors while they hold headroom.

`open_code` is invisible to quota-axi.

## When a role needs a specific model or effort

Skip `delegate_to_agent` and the sidekick lane; run the CLI directly through Bash in the background. Per-invocation flags touch no shared state, so parallel arms cannot race each other.

```
codex exec -m <model> -c model_reasoning_effort=<low|medium|high|xhigh|max|ultra> "<prompt>"
grok -m <model> --output-format <fmt> "<prompt>"
cursor-agent -p --model <slug> --output-format json "<prompt>"
opencode run -m <provider/model> "<prompt>"
```

`cursor-agent --list-models` and `opencode models` enumerate what is actually available. Never mutate a CLI's config file to steer one delegation; that value is shared with every other delegation and with whatever the user is doing in another terminal.

## Where model and effort live

| Agent | Config |
|---|---|
| `claude_code` | `~/.claude/settings.json` |
| `codex` | `~/.codex/config.toml` |
| `grok` | `~/.grok/config.toml` |
| `open_code` | `~/.config/opencode/opencode.json` |
| `cursor` | codeg Agent defaults tab (`CURSOR_MODEL`) |

Read the file when the current value matters; a copy here would go stale.
