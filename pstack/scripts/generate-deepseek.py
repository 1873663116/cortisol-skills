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
        "a `subagent` call, which returns at once and notifies you when it finishes",
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
    (r"~/.cursor/rules/pstack-models\.mdc", "~/.agents/pstack-models.md"),
    (r"`pstack-models\.mdc`", "`pstack-models.md`"),
    (r"pstack-models\.mdc", "pstack-models.md"),
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
