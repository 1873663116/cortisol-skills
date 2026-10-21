---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for /skill:swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
disable-model-invocation: true
---

# Swarm

This copy is generated for Pi and already uses Pi tool names. Read [the Pi adapter](~/.agents/pstack/docs/harness/pi.md) once per session for the rows a generated tree cannot change: subagent capability, isolation, model roles, and session transcripts.

## Start

Open a todolist with one entry per phase before launching anything.

1. Frame
2. Fan out
3. Aggregate
4. Report

## Phase A: Frame

1. State the done predicate and the artifact or report the swarm must return.
2. Choose the shape. Partition into slices, race N workers on identical briefs, or mix both. For a race or mixed shape, declare `first pass`, `rank all`, or `best-of` before spawning.
4. Pick the worker agent from the `swarm workers` line in `~/.pi/agent/pstack-models.md`. If the file or that line is missing, use `grok-4.7-xhigh-fast`. An `auto` or `inherit-parent` value means an agent with no `model` field, so the workers run on the parent model. The `subagent` tool takes no `model` parameter: an agent file must already name the model, and when none does, say so and use the closest available agent. For a model race, name each arm's agent and model up front.
5. Give each worker its own writable output when it writes. When workers verify or measure commits, each brief names the exact SHAs. A measurement brief also names the method (sample count, what one sample is, order). The worker records both in its result.

## Phase B: Fan out

Spawn all N workers in one message, one `subagent` call per worker, each call returning when that worker finishes. Run each in a `git worktree` named in the brief, and use the step 4 agent. Use the current working directory only when the worker needs access to something on the user's computer.

When a worker must start from a non-default pushed branch, check it out in its worktree before it starts.

Every brief stands alone. Include the goal, scope, exact slice or race arm, how to verify, and what to report. Reports use `PASS`, `ISSUES`, or `BLOCKED` with evidence. A worker that can prove a defect reports `ISSUES` and lists every issue it can prove, not only the first.

If a worker drops out, proceed with N-1 and note it.

## Phase C: Aggregate

Read the terminal results. Drop a result that does not record the SHAs and method its brief names, and respawn that worker once. After a second miss, record a gap. A gap does not count as a pass. For coverage, every required slice needs a result. For a race, apply the selection rule declared up front. Use first pass, rank all, or best-of. Do not paste raw worker dumps.

## Phase D: Report

Return one consolidated in-chat report with the table, issue one-liners, gaps or dropouts, and the race rule when used.
