/**
 * Tomato-mode sticky reminder.
 *
 * A skill body enters context only on the turn it is invoked. In a long
 * conversation the routing rule then fades, and the model stops treating a
 * later request as work the mode should route. Cursor solves this with a
 * Custom Mode that re-injects the whole skill every turn. That costs the full
 * body on every request and, being ordinary history, is the first thing a
 * compaction pass drops.
 *
 * This plugin re-states one line instead, at the start of each turn, and only
 * while the mode is on. One line is enough because the body is already in the
 * conversation; the line only names it again and carries its path for the case
 * where compaction removed the body.
 *
 * Semantics, which match a `UserPromptSubmit` hook:
 *
 *   prompt carries /tomato-mode    -> turn the mode on
 *   prompt carries /tomato-off     -> turn it off
 *   mode on, first step of a turn  -> one reminder on the surface
 *   mode on, later steps           -> nothing added
 *   next turn                      -> the reminder is replaced, not stacked
 *
 * Detection reads the user messages the loop already claimed for this turn, so
 * the state follows what the user typed rather than what the model chose.
 *
 * The reminder is a surface node this plugin owns. Each turn replaces the
 * previous node in place, so the model sees exactly one reminder however long
 * the conversation runs, and compaction never has to carry a pile of them.
 */

import { randomUUID } from "node:crypto";

export const name = "tomato-reminder";

export const inject = [];

/**
 * Build a frozen user message.
 *
 * `createUserMessage` from `@deepseek-ai/dsh-llm` does the same thing, but a
 * profile-loaded plugin resolves bare specifiers against the profile root,
 * where that package is not installed, so the shape is built here instead. The
 * fields are the whole contract: a role, content blocks, a source label, and a
 * stable id.
 *
 * @param text - the message text.
 * @param source - the producer label stamped on the message.
 * @returns a frozen user message.
 */
function userMessage(text, source) {
    return Object.freeze({
        id: randomUUID(),
        role: "user",
        content: Object.freeze([Object.freeze({ type: "text", text })]),
        source: Object.freeze({ ...source }),
    });
}

/** Label every injected message so it never reads as a user prompt. */
const SOURCE = { kind: "tomato-reminder", form: "notice" };

/** Sigils accepted for each control, since harnesses disagree on the prefix. */
const ON = /(^|\s)\/tomato-mode(?=\s|$)/;
const OFF = /(^|\s)\/tomato-off(?=\s|$)/;

/** Per-agent mode state plus the seq of the surface node this plugin owns. */
const state = new WeakMap();

function stateOf(agent) {
    let entry = state.get(agent);
    if (entry === undefined) {
        entry = { on: false, seq: undefined };
        state.set(agent, entry);
    }
    return entry;
}

function textOf(message) {
    return (message.content ?? [])
        .filter((block) => block.type === "text")
        .map((block) => block.text)
        .join("\n");
}

/**
 * Update the mode state from this turn's user input.
 * @param entry - the agent's state, mutated in place.
 * @param messages - messages the loop claimed for this turn.
 * @returns whether the state changed on this turn.
 */
function observe(entry, messages) {
    let changed = false;
    for (const message of messages) {
        if (message.source?.kind !== "user") continue;
        const text = textOf(message);
        if (OFF.test(text)) {
            if (entry.on) changed = true;
            entry.on = false;
        } else if (ON.test(text)) {
            if (!entry.on) changed = true;
            entry.on = true;
        }
    }
    return changed;
}

/**
 * Build the reminder line.
 * @param skillPath - absolute path to the mode skill, carried for the case
 *   where compaction removed the body from the conversation.
 * @returns the one-line reminder.
 */
function reminder(skillPath) {
    return `Tomato mode is on. Match a playbook before acting; if the skill body is no longer in context, read ${skillPath}. A casual turn, or one where the operator opts out, does not need it.`;
}

/**
 * Install the listener.
 * @param ctx - plugin context; the listener is disposed with it.
 * @param config - resolved configuration.
 */
export function apply(ctx, config) {
    const skillPath =
        config?.skillPath ??
        "/Users/xiongzhipeng/.agents/skills/tomato-mode/SKILL.md";

    ctx.on("agent/pre-step", async ({ agent, messages, step }, next) => {
        const entry = stateOf(agent);
        observe(entry, messages);

        if (step !== 1) return next();

        const decision = await next();
        if (decision.kind === "reject") return decision;

        const session = agent.session;

        // Turning the mode off removes the node instead of leaving a stale
        // claim that the mode is on.
        if (!entry.on) {
            if (entry.seq === undefined) return decision;
            try {
                session.append(
                    "user/message",
                    userMessage("", SOURCE),
                    {
                        surfaceOp: {
                            op: "replace",
                            startSeq: entry.seq,
                            endSeq: entry.seq,
                        },
                        sourceEventSeqs: [entry.seq],
                    },
                );
            } catch {
                // The node is already gone; nothing left to remove.
            }
            entry.seq = undefined;
            return decision;
        }

        const message = userMessage(reminder(skillPath), SOURCE);

        if (entry.seq !== undefined) {
            try {
                const replaced = session.append("user/message", message, {
                    surfaceOp: {
                        op: "replace",
                        startSeq: entry.seq,
                        endSeq: entry.seq,
                    },
                    sourceEventSeqs: [entry.seq],
                });
                entry.seq = replaced.seq;
                return decision;
            } catch {
                entry.seq = undefined;
            }
        }

        entry.seq = session.append("user/message", message, {
            surfaceOp: "append",
        }).seq;
        return decision;
    });
}
