import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const SKILL_PATH = join(homedir(), ".pi", "agent", "skills", "tomato-mode", "SKILL.md");

const REMINDER = `Tomato mode is on. Match a playbook before acting; if the skill body is no longer in context, read ${SKILL_PATH}. A casual turn, or one where the operator opts out, does not need it.`;

export default function tomatoReminder(pi: ExtensionAPI): void {
	let enabled = false;

	pi.registerCommand("tomato-mode", {
		description: "Turn tomato mode on and load the pstack playbook skill",
		handler: async (_args, ctx) => {
			let body: string;
			try {
				body = readFileSync(SKILL_PATH, "utf8");
			} catch {
				ctx.ui.notify(`Cannot read ${SKILL_PATH}`, "error");
				return;
			}
			enabled = true;
			await pi.sendUserMessage(body);
		},
	});

	pi.registerCommand("tomato-off", {
		description: "Turn tomato mode off",
		handler: async (_args, ctx) => {
			enabled = false;
			ctx.ui.notify("Tomato mode off.", "info");
		},
	});

	pi.on("before_agent_start", async (event) => {
		if (!enabled || event.messageType !== "user") return;
		return {
			message: {
				customType: "tomato-reminder",
				content: REMINDER,
				display: false,
			},
		};
	});

	pi.on("context", async (event) => {
		const reminderSeqs: number[] = [];
		event.messages.forEach((message, index) => {
			if ((message as { customType?: string }).customType === "tomato-reminder") {
				reminderSeqs.push(index);
			}
		});
		if (reminderSeqs.length === 0) return;
		const keep = enabled ? reminderSeqs[reminderSeqs.length - 1] : -1;
		return {
			messages: event.messages.filter(
				(_message, index) => !reminderSeqs.includes(index) || index === keep,
			),
		};
	});
}
