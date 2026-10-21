# Prompts worth copying

Swap in the real paths, skills, and done checks. Informal wording works.

## Understand

- `/skill:tomato-mode read <thread>. restate the underlying issue in your own words, in plain english.`
- `/skill:in-your-own-words <long or messy ask>`
- `/skill:sharpen <your task>`
- `/skill:tomato-mode investigate why <symptom>. give me what we know, what data you used, and your best hypotheses. don't change any code yet.`
- `use /skill:how to understand <subsystem>. then use /skill:why to find out why it broke recently.`
- `/skill:recall my work on <topic> from last week, then read <issue>.`
- `/skill:teach me why you implemented it this way and not <other way>. what did you trade off?`
- `/skill:tomato-mode take over this branch. read the decision log, find what's done, and continue. don't redo finished work.`

## Build

- Bug: `/skill:tomato-mode <symptom>. repro first, then fix and verify.`
- Bug in an app: `/skill:tomato-mode repro this with /skill:verify-<app>. if it repros on main, fix it and show me a video as proof.`
- Bug with a cheap test: `/skill:tomato-mode repro <bug> first. if there's a cheap test path, /skill:tdd it. then fix and rerun.`
- Feature: `/skill:tomato-mode add <behavior>. <current output> stays byte-identical. verify both.`
- Refactor: `/skill:tomato-mode move <code> into one module, zero behavior change. record the current output first and prove it's unchanged after.`
- Perf: `/skill:tomato-mode <operation> takes <time> on <fixture>. trace it, fix the measured cause, show me before and after.`

## Design and plan

- `/skill:tomato-mode prototype a few options for <feature>. take screenshots or videos for me to compare.`
- `/skill:tomato-mode we need <feature>. /skill:architect it first, and answer open questions with prototypes. let me review before proceeding.`
- `/skill:tomato-mode write a tutorial for how i would use <new package> first. then /skill:teach me why it beats the current one.`
- `ask /skill:arena for a second opinion on this thread and our approach.`
- `/skill:tomato-mode turn this design into a plan. small verifiable PRs, each with its own verification steps.`
- `/skill:tomato-mode plan the migration of <library> to <target>. small verifiable PRs. the result must match the original exactly, bugs included.`

## Review and ship

- `/skill:interrogate the whole branch, but skeptically. don't change anything yet. no nitpicks unless it's a real bug or regression.` Read the dismissals too.
- `/skill:swarm check every package under <dir> against its check script. one worker per package. one report.`
- `/skill:tomato-mode open the pr. small ordered commits, evidence in the description.`
- `/skill:tomato-mode babysit this pr. get it green.` For status only: `/skill:tomato-mode check on pr <number>. anything outstanding?`
- `/skill:tomato-mode land the stack.`

## Away and back

- `/skill:tomato-mode im going to bed. <goal> in a fresh worktree off <base>. done means <checks>. keep a decision log. don't ask me before committing. Repeat until done. if you're truly stuck after a few hours, stop and write up why.`
- `/skill:show-me-your-work catch me up on what you did last night.` Read its Attention section first.
- `/skill:tomato-mode full autopilot on this queue. each item is independent.`
- `/skill:tomato-mode autopilot these changes but stack them, don't ship. i'll land the stack.`
- `/skill:reflect capture what we learned so the next run doesn't repeat it.` Approve only edits that change a future decision.
- `/skill:bro` restates the last reply in plain words.
