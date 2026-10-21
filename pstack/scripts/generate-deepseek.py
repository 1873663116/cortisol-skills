#!/usr/bin/env python3
"""Generate the DeepSeek Harness tree from the pstack skills.

pstack is written in Cursor's tool vocabulary. Two hosts consume it:

  DeepSeek Harness   reads  ~/.dsh/skills           (rank 400)
  Claude Code        reads  ~/.agents/skills         (rank 500)

DSH scans both roots and, within one layer, the lower rank wins a duplicate
name. So the two trees sit side by side, each host finds its own copy first,
and no runtime detection is needed to pick one: the host routes itself by
where it looks. `scripts/check-upstream.py` produces the Claude Code tree;
this script turns that tree into the DSH one.

Only tool names, field names, and paths are rewritten. Prose is untouched, so
both trees read the same and an upstream change ports to both from one input.

Usage:
  generate-deepseek.py            write the tree
  generate-deepseek.py --check    report drift and exit non-zero
"""

import argparse
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
SOURCE = os.path.join(REPO, "skills")
OUT = os.path.join(ROOT, "generated", "deepseek", "skills")

# Skills this repo owns rather than ports. They speak Claude Code and stay out
# of the DSH tree until they are ported on their own.
LOCAL_ONLY = {
    "find-skills",
    "grilling",
    "handoff",
    "mole",
    "prompt-engineering",
    "subagent-dispatch",
    "writing-for-agents",
    "wtf",
}

# A backticked code span holding a tool name becomes the DSH tool name.
SPAN = {
    "Task": "subagent",
    "AskQuestion": "ask_user_question",
    "AskUserQuestion": "ask_user_question",
    "TodoWrite": "todo_write",
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Grep": "grep",
    "Glob": "glob",
    "Bash": "bash",
    "Skill": "skill",
    "generalPurpose": "subagent",
}

# A bare mention becomes a code span, so the model sees the tool name as a
# name. Longest phrase first; the last row is the catch-all.
BARE = [
    (r"\bthe Task tool\b", "the `subagent` tool"),
    (r"\bthe Task subagent\b", "the `subagent` tool"),
    (r"\bTask subagent\b", "`subagent`"),
    (r"\bTask calls\b", "`subagent` calls"),
    (r"\bTask call\b", "`subagent` call"),
    (r"\bAskQuestion tool\b", "`ask_user_question` tool"),
    (r"\bAskQuestion\b", "`ask_user_question`"),
    (r"\bAskUserQuestion\b", "`ask_user_question`"),
    (r"\bthe Task\b", "`subagent`"),
    (r"\bTask\b", "`subagent`"),
]

# Cursor subagent fields the DSH `subagent` tool does not accept. Each becomes
# the instruction that carries the same intent: no type, no readonly flag, no
# cloud flag, no background flag.
FIELD_RULES = [
    (
        "`subagent_type: generalPurpose`, `readonly: true`",
        "one `subagent` call, no file writes",
    ),
    (
        "`subagent_type: generalPurpose`, `environment: \"cloud\"`, `run_in_background: true`",
        "one `subagent` call, a worktree named in the brief",
    ),
    (
        "`subagent_type: generalPurpose`, `readonly: false`",
        "one `subagent` call, full tool set",
    ),
    (
        "`subagent_type: generalPurpose`",
        "`subagent`",
    ),
    (
        "`subagent_type: \"tomato-agent\"`",
        "`subagent` carrying `tomato-agent`'s instructions in the brief",
    ),
    (
        "`subagent_type: \"comment-sicko\"`",
        "`subagent` carrying `comment-sicko`'s instructions in the brief",
    ),
    (
        '`environment: "cloud"`',
        "a `git worktree` you name in the brief",
    ),
    (
        '`environment: "local"`',
        "the current working directory",
    ),
    (
        "`readonly: true`",
        "no file writes: say so in the brief, then check `git status` afterward",
    ),
    (
        "`readonly: false`",
        "the full tool set, MCP servers included",
    ),
    (
        "`run_in_background: true`",
        "a call that returns at once and notifies you when it finishes",
    ),
    (
        "`resume`",
        "`send_message` to the child, or a fresh `subagent` with the earlier result pasted in",
    ),
    (
        "`file_attachments`",
        "the paths in the brief",
    ),
]

# Paths that name another host's layout. Longest and most specific first: a
# short rule fired early would rewrite the prefix of a longer path.
PATH_RULES = [
    # Transcript trees.
    (
        r"~/.cursor/projects/<slug>/agent-transcripts/<uuid>/<uuid>\.jsonl",
        "~/.dsh/sessions/<slug>/session-<uuid>/session.v4.jsonl.zstd",
    ),
    (
        r"~/.claude/projects/<slug>/\*\.jsonl",
        "~/.dsh/sessions/<slug>/session-*/session.v4.jsonl.zstd",
    ),
    (r"~/.claude/projects/<slug>", "~/.dsh/sessions/<slug>"),
    (
        r"~/\.cursor/projects/\*/agent-transcripts",
        "~/.dsh/sessions/*",
    ),
    (r"~/\.cursor/projects/", "~/.dsh/sessions/"),
    (r"\.cursor/projects/", "~/.dsh/sessions/"),
    # Model rule, which DSH has no rules directory for.
    (r"~/.cursor/rules/pstack-models\.mdc", "~/.agents/AGENTS.md"),
    (r"`pstack-models\.mdc`", "`AGENTS.md`"),
    (r"pstack-models\.mdc", "AGENTS.md"),
    # Skill and plugin roots.
    (r"~/.cursor/skills/", "~/.dsh/skills/"),
    (r"\.cursor/skills/", "~/.dsh/skills/"),
    (r"~/.cursor/plugins/", "~/.dsh/plugins/"),
    (r"\.cursor/worktrees/", "worktrees/"),
    (r"\.cursor/rules/", "~/.agents/"),
    (r"\.cursor/", "~/.dsh/"),
    # Transcript directory by bare name.
    (r"agent-transcripts/", "`session-*/`"),
]

# A few files carry host-specific mechanics that no token rewrite reaches. Each
# pair replaces a whole block with the DSH equivalent.
BLOCK_RULES = [
    # DSH writes zstd-compressed session logs one level deeper, so the plain
    # recursive search the Claude Code script uses cannot read them.
    (
        """# Transcripts dir: ~/.cursor/projects/<slugified-repo-path>/agent-transcripts.
slug=$(printf '%s' "$main_wt" | sed 's#^/##; s#/#-#g')
transcripts="$HOME/.cursor/projects/$slug/agent-transcripts"
""",
        """# Sessions live at ~/.dsh/sessions/<slugified-repo-path>/session-*/session.v4.jsonl.zstd.
# They are zstd-compressed, so the scan decompresses each newest log before matching.
slug=$(printf '%s' "$main_wt" | sed 's#^/##; s#/#-#g')
sessions="$HOME/.dsh/sessions/$slug"
""",
    ),
    (
        """	if [ -d "$transcripts" ]; then
		f=$(rg -l -e "${wt}/" -e "${wt}\\\"" "$transcripts" 2>/dev/null \\
			| xargs stat -f '%m %N' 2>/dev/null | sort -rn | head -1)
		if [ -n "$f" ]; then last_ts=$(echo "$f" | awk '{print $1}')
			last=$(date -r "$last_ts" '+%Y-%m-%d' 2>/dev/null); fi
	fi
""",
        """	if [ -d "$sessions" ]; then
		f=$(ls -t "$sessions"/session-*/session.v4.jsonl.zstd 2>/dev/null | while read -r log; do
			if zstd -dc "$log" 2>/dev/null | rg -q -e "${wt}/" -e "${wt}\\\""; then stat -f '%m %N' "$log"; fi
		done | sort -rn | head -1)
		if [ -n "$f" ]; then last_ts=$(echo "$f" | awk '{print $1}')
			last=$(date -r "$last_ts" '+%Y-%m-%d' 2>/dev/null); fi
	fi
""",
    ),
    (
        "Write `~/.cursor/rules/pstack-models.mdc`, an always-applied rule that sets pstack's model per role.",
        "Write pstack's model roles into `~/.agents/AGENTS.md`, the user-global instruction file this harness loads into every session. Replace only the delimited pstack region and leave the rest of that file alone.",
    ),
    (
        'The default role-to-model mapping is the rule shape shown in step 5 below. If `~/.cursor/rules/pstack-models.mdc` already exists, read it and treat its `# budget` line and its role values as the current choices.',
        'The default role-to-model mapping is the shape shown in step 5 below. If `~/.agents/AGENTS.md` already holds a pstack region, read it and treat its `# budget` line and its role values as the current choices.',
    ),
    (
        "Enumerate the model slugs you can pass to a `Task` subagent in this session. That is the dependable source. If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness. If you cannot detect any, ask the user to paste the slugs they have access to. Never write a real slug you have not confirmed is available. The aliases `inherit-parent` and `auto` are always valid even though they are not detected slugs.",
        'Call `list_subagent_models`. It reports the exact provider and model routes this session may name, which is the only dependable source. If the tool is absent, model selection is off for this composition, so say so and leave the role table on its defaults. Never write a route you have not confirmed. The aliases `inherit-parent` and `auto` are always valid even though they are not routes.',
    ),
    (
        "**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these four options with these exact labels, and name the current budget when the rule records one. With no rule, say that `large` matches the skill defaults.\n\n- `unlimited — max reasoning`\n- `large — xhigh reasoning`\n- `medium — high reasoning`\n- `small — medium reasoning`\n\n**(b) Apply it.** Build the working table from the skill defaults, and on a re-run keep any role you changed by family, list, or alias (`inherit-parent`, `auto`). `unlimited`, `large`, `medium`, and `small` set the effort token of every real slug, panel entries included, to `max`, `xhigh`, `high`, or `medium`. The effort token is the last token, or the one before a trailing `fast`, on the ladder `max` > `xhigh` > `high` > `medium` > `low`. If the result is not a detected slug, use the same family's detected slug with the highest effort at or below the target, else mark the role as needing a choice. `inherit-parent` and `auto` do not change. So `unlimited` turns `claude-opus-5-5-xhigh` into `claude-opus-5-5-max`. Grok slugs top out at `xhigh`, so under `unlimited` the fallback puts Grok at `xhigh` and keeps `grok-4.7-xhigh-fast` as it is. `large` keeps both defaults. `small` turns them into `claude-opus-5-5-medium` and `grok-4.7-medium-fast`.\n",
        "**(a) Ask for a budget.** Prefer AskQuestion over free text. Offer these three options with these exact labels, and name the current budget when the region records one. With no region, say that `large` matches the skill defaults.\n\n- `unlimited: max reasoning`\n- `large: high reasoning`\n- `small: low reasoning`\n\n**(b) Apply it.** The budget sets `reasoning_effort`, and only on routes that declare efforts. In this deployment the `deepseek*` routes declare `max`, `high`, and `low`; every other route ignores the setting. Build the working table from the skill defaults, and on a re-run keep any role you changed by route (`inherit-parent`, `auto` included). `unlimited` sets every role to `max`, `large` to `high`, `small` to `low`. Keep each role's route, so a diverse panel stays diverse. `inherit-parent` and `auto` do not change.\n\n",
    ),
    (
        'Every real slug written must be in the detected set. `inherit-parent` and `auto` always pass. If a chosen real slug is not available, stop and ask again.',
        'Every route written must appear in what `list_subagent_models` returned. `inherit-parent` and `auto` always pass. If a chosen route is not available, stop and ask again.',
    ),
    (
        'Write `~/.cursor/rules/pstack-models.mdc` with `alwaysApply: true`, a `# budget` line with the chosen label and its target effort, and one line per role, using the same labels tomato-mode uses. Overwrite the whole file so re-runs stay idempotent. Shape:\n\n```\n---\ndescription: pstack per-role model choices (overrides skill defaults)\nalwaysApply: true\n---\n# pstack model configuration. One line per role. Delete a line to fall back to the skill default.\n# `inherit-parent` or `auto` as a value: the role runs on the parent chat model (omit Task `model`). Alias entries in a panel list still count toward its fan-out.\n# budget: large (xhigh)\nfeature, refactoring: grok-4.7-xhigh-fast\nbug-fix: grok-4.7-xhigh-fast\nperf-issue: grok-4.7-xhigh-fast\nhillclimb: grok-4.7-xhigh-fast\njudgment and prose: claude-opus-5-5-xhigh\nhardest tasks: claude-opus-5-5-xhigh\nhow explorer: grok-4.7-xhigh-fast\nhow explainer: claude-opus-5-5-xhigh\nwhy investigators: grok-4.7-xhigh-fast\nwhy synthesizer: claude-opus-5-5-xhigh\nreflect tooling: grok-4.7-xhigh-fast\nreflect judgment, divergent, synthesizer: claude-opus-5-5-xhigh\narena runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast\narena cross-judge pool: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast\nswarm workers: grok-4.7-xhigh-fast\narchitect runners: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast\ninterrogate reviewers: claude-opus-5-5-xhigh, grok-4.7-xhigh-fast\n```\n\n### 6. Confirm\n\nTell the user the rule was written and that it applies to new sessions. Re-running this skill updates it.\n\n### 7. Offer a verification skill (optional)\n\nCheck whether the project has a way to drive the real app for proof (a `verify-*` skill, or an existing harness). If not, offer once: "want a project-local verification skill, so agents can drive the app the way a user does and prove changes work? I can generate one with /create-verification-skill." On yes, invoke `/create-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.\n\n### 8. Offer a formal verification skill (optional)\n\nCheck whether the project already has a formal verification skill (a project skill that runs a model checker, a proof, or another verifier against the code). If not, offer once: "want a formal verification skill, so agents can prove a key property of your code holds in every case in scope, not only the cases tests reach? I can generate one with /create-formal-verification-skill." On yes, invoke `/create-formal-verification-skill` (resolves wherever pstack is installed: workspace, user, or plugin). On no, move on without pushing.\n',
        'Write the region into `~/.agents/AGENTS.md` between `<!-- pstack-models:start -->` and `<!-- pstack-models:end -->`. Replace only that region so the rest of the file survives, and append it when missing. Shape:\n\n```\n<!-- pstack-models:start -->\n# pstack model configuration. One line per role. Delete a line to fall back to the skill default.\n# A value is a provider and model as `list_subagent_models` reports them, written `provider / model`. `inherit-parent` or `auto` runs the role on the parent model.\n# budget: large (high)\nfeature, refactoring: command-code / deepseek/deepseek-v4.1-flash\nbug-fix: command-code / deepseek/deepseek-v4.1-flash\nperf-issue: command-code / deepseek/deepseek-v4.1-flash\nhillclimb: command-code / deepseek/deepseek-v4.1-flash\njudgment and prose: command-code / gpt-6-luna\nhardest tasks: command-code / gpt-6-luna\nhow explorer: command-code / deepseek/deepseek-v4.1-flash\nhow explainer: command-code / gpt-6-luna\nwhy investigators: command-code / deepseek/deepseek-v4.1-flash\nwhy synthesizer: command-code / gpt-6-luna\nreflect tooling: command-code / deepseek/deepseek-v4.1-flash\nreflect judgment, divergent, synthesizer: command-code / gpt-6-luna\narena runners: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash\narena cross-judge pool: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash\nswarm workers: command-code / deepseek/deepseek-v4.1-flash\narchitect runners: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash\ninterrogate reviewers: command-code / gpt-6-luna, command-code / deepseek/deepseek-v4.1-flash\n<!-- pstack-models:end -->\n```\n\n### 6. Confirm',
    ),
]


# `reflect` opens by locating the current transcript. DSH stores one compressed
# log per session instead of a JSONL tree, so the whole discovery step differs.
HOST_RULES = [
    (
        "If Cursor also exposes a models API or CLI that lists the user's entitled models, prefer it for completeness.",
        "If the session exposes `list_subagent_models`, use it: it reports the providers, models, and reasoning efforts this route policy allows.",
    ),
]

REFLECT_RULES = [
    (
        "find this conversation's transcript in the `agent-transcripts/` directory the system prompt names. Do not glob across `~/.cursor/projects/*/`. That crosses workspace boundaries and reads private chats from unrelated projects.",
        "find this conversation's session log under `~/.dsh/sessions/<slug>/`. Do not scan other slugs: each one is another workspace and may hold private chats.",
    ),
    (
        "ls -t <agent-transcripts>/*.jsonl <agent-transcripts>/*/*.jsonl <agent-transcripts>/*/subagents/*.jsonl 2>/dev/null | head -10",
        "ls -t ~/.dsh/sessions/*/session-*/session.v4.jsonl.zstd 2>/dev/null | head -10",
    ),
    (
        "That covers the legacy flat (`<id>.jsonl`), current nested (`<id>/<id>.jsonl`), and subagent (`<parent>/subagents/<child>.jsonl`) layouts. For each candidate, read the first JSONL line. Take the file whose `message.content[0].text` contains the conversation's opening user prompt. If none matches, pass a tight digest of the session instead.",
        "Each log is zstd-compressed, so decompress before reading: `zstd -dc <log> | head -1`. Take the newest log whose opening user prompt matches. Subagent turns are recorded in the same log. If none matches, pass a tight digest of the session instead.",
    ),
]

ADAPTER_FROM = (
    "This local port runs pstack under Claude Code. Read "
    "[the Claude Code adapter](../../pstack/docs/harness/claude-code.md) once per session "
    "before you follow this skill: it maps every Cursor name in pstack skills to its "
    "Claude Code equivalent."
)
ADAPTER_TO = (
    "This copy is generated for DeepSeek Harness and already uses DSH tool names. Read "
    "[the DSH adapter](../../../../docs/harness/deepseek.md) once per session for the rows "
    "a generated tree cannot change: subagent capability, isolation, model roles, and "
    "session transcripts."
)

CODE_EXT = (".md", ".mjs", ".ts", ".json", ".sh", ".lock", ".py")


def rewrite_span(match):
    inner = match.group(1)
    return "`" + SPAN.get(inner, inner) + "`"


# Cursor model slugs this deployment cannot route. Two families carry every
# default in the tree: the fast code family and the judgment family. Each maps
# onto one configured route, so a skill that names a default still names a route
# `subagent` accepts. Applied last: nothing downstream reads a slug.
MODEL_RULES = [
    (r"claude-opus-5-5-(?:xhigh|max|medium|low)(?:-fast)?", "gpt-6-luna"),
    (r"claude-opus-5-5", "gpt-6-luna"),
    (r"grok-4\.7-(?:xhigh|max|medium|low)(?:-fast)?", "deepseek/deepseek-v4.1-flash"),
    (r"grok-4\.7", "deepseek/deepseek-v4.1-flash"),
    (r"`gpt-6-luna`", "`command-code / gpt-6-luna`"),
    (r"`deepseek/deepseek-v4\.1-flash`", "`command-code / deepseek/deepseek-v4.1-flash`"),
]

# Prose that names a Cursor field or a Cursor model family without a backtick
# span or a slug the rules above reach either.
TEXT_RULES = [
    (
        "set their own `subagent_type` for diverse-model review",
        "pick their own `provider` and `model` for diverse-model review",
    ),
    (
        "agent mode (readonly strips MCP)",
        "no file writes unless the brief says otherwise",
    ),
    (
        "Families go by prefix: `claude-*`, and `grok-*` with `cursor-grok-*` and `composer-*`.",
        "Families go by route: the judgment route and the code route.",
    ),    (
        "**Do not use readonly/Ask mode.** It strips MCP access, which disables the MCP-backed investigators and the synthesizer's citation spot-checks.",
        "**Do not ask for a reduced tool set.** The MCP-backed investigators and the synthesizer's citation spot-checks need it.",
    ),
    (
        "and readonly strips MCPs.",
        "and a reduced tool set would strip them.",
    ),
    (
        " (agent mode)",
        "",
    ),
    (
        ", agent mode (the full tool set, MCP servers included)",
        ", the full tool set, MCP servers included",
    ),
    (
        "Spawn one readonly judge subagent on that model.",
        "Spawn one judge subagent on that route that writes no files.",
    ),
    (
        "`/setup-pstack` budget sets each role's starting level, xhigh by default. Raise it one step, up to max, for the hardest or subtlest work. Lower it one step for judgment and two or more steps for routine work.",
        "`/setup-pstack` budget sets each role's starting level, `high` by default. Use `max` for the hardest or subtlest work and `low` for routine work.",
    ),
    (
        "Otherwise use standard speed, the same slug without `-fast`.",
        "Otherwise use the route as written.",
    ),
    (
        "Change only the effort level and whether the slug is fast, and keep the family the role names, so a diverse panel stays diverse. If the family has no slug at that level and speed, use its nearest slug.",
        "Change only the effort level, and keep the route the role names, so a diverse panel stays diverse. If a route declares no effort, leave it unset.",
    ),
    (
        "If the `subagent` tool rejects the adjusted slug, do not try another adjusted slug.",
        "If the `subagent` tool rejects an adjusted route, do not try another one.",
    ),    (
        "marking any real slug not in the detected set as needing a choice",
        "marking any route not in the detected set as needing a choice",
    ),
]


def transform(text):
    text = text.replace(ADAPTER_FROM, ADAPTER_TO)
    for before, after in BLOCK_RULES:
        text = text.replace(before, after)
    for before, after in REFLECT_RULES:
        text = text.replace(before, after)
    for before, after in HOST_RULES:
        text = text.replace(before, after)
    # The generated tree sits one directory deeper than the skill source, so
    # every link that climbed to `pstack/` needs one more level.
    # From `skills/<name>/`, four levels up is `pstack/`.
    text = text.replace("](../../pstack/", "](../../../../")
    if text is None:
        raise AssertionError
    for literal, replacement in FIELD_RULES:
        text = text.replace(literal, replacement)
    text = re.sub(r"`([A-Za-z][A-Za-z0-9_]*)`", rewrite_span, text)
    for pattern, replacement in BARE:
        text = re.sub(pattern, replacement, text)
    for pattern, replacement in PATH_RULES:
        text = re.sub(pattern, replacement, text)
    for before, after in TEXT_RULES:
        text = text.replace(before, after)
    for pattern, replacement in MODEL_RULES:
        text = re.sub(pattern, replacement, text)
    return text


def walk(base):
    for dirpath, _, names in os.walk(base):
        for name in sorted(names):
            if name == ".DS_Store":
                continue
            full = os.path.join(dirpath, name)
            yield os.path.relpath(full, base), full


def build():
    files = {}
    for rel, full in walk(SOURCE):
        top = rel.split(os.sep, 1)[0]
        if top in LOCAL_ONLY:
            continue
        data = open(full, "rb").read()
        if rel.endswith(CODE_EXT):
            try:
                data = transform(data.decode("utf-8")).encode("utf-8")
            except UnicodeDecodeError:
                pass
        files[rel] = (data, os.stat(full).st_mode & 0o111)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = build()
    if args.check:
        on_disk = {}
        if os.path.isdir(OUT):
            on_disk = {rel: open(full, "rb").read() for rel, full in walk(OUT)}
        drifted = sorted(
            p for p in set(files) | set(on_disk)
            if p not in files or p not in on_disk or files[p][0] != on_disk[p]
        )
        for path in drifted:
            print(f"generated/deepseek/skills/{path}")
        print(f"{len(drifted)} file(s) drifted of {len(files)}.")
        return 1 if drifted else 0

    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    for rel, (data, mode) in files.items():
        target = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(target) or OUT, exist_ok=True)
        with open(target, "wb") as fh:
            fh.write(data)
        os.chmod(target, 0o755 if mode else 0o644)
    print(f"{len(files)} file(s) written to {os.path.relpath(OUT, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
