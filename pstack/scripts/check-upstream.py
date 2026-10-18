#!/usr/bin/env python3
"""Report what changed in upstream pstack since the pinned baseline.

Upstream ships two trees. `pstack/` is Cursor's; `harness/pstack/claude-code/`
is a generated Claude Code copy that already carries the adapter line and the
local link targets. This fork ports the generated tree, so the baseline here is
`harness/pstack/claude-code`, not `pstack/skills`.

Splits every upstream change by whether this fork has touched that file, which
is the only question that decides how much judgment the update needs:

  TAKE    upstream changed it, we never did. Apply the transforms in PORT.md
          and write it over the local file.
  REVIEW  upstream changed it and so did we. Both diffs are printed; a human or
          an agent decides what the merged text should say.
  NEW     upstream added a file. Decide whether it belongs in this port.
  GONE    upstream deleted a file we still carry.

This script reports. It never edits, merges, or re-pins; those are judgment
calls that belong to whoever reads the report.

Usage:
  check-upstream.py              compare pinned baseline against upstream HEAD
  check-upstream.py --ref <sha>  compare against a specific upstream commit
  check-upstream.py --diffs      also print the actual diffs for REVIEW files
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
PIN_FILE = os.path.join(ROOT, "UPSTREAM")

# Upstream generates the Claude Code tree under this path. Its files land in
# this fork as shown by local_path() and read differently by transform().
TREE = "harness/pstack/claude-code"

# Local name of the routing skill and the help skill. Upstream still uses the
# poteto names, which the folder rename alone does not reach: the names appear
# in frontmatter, in prose, in cross-links, and in the scripts.
RENAMED = {"poteto-mode": "tomato-mode", "poteto-help": "tomato-help"}

# Files whose local name differs from the tree's. Renaming the poteto folders
# leaves the filenames inside them, so both levels are mapped here.
FILE_RENAMES = {
    "docs/guide/02-poteto-mode.md": "docs/guide/02-tomato-mode.md",
    "agents/poteto-agent.md": "agents/tomato-agent.md",
}

# Skill folders kept out of the port. Empty today; make-bot-ui ships in the
# generated tree, so it installs like every other skill.
NOT_INSTALLED = set()

# Files the fork drops after copying.
DELETED_PATHS = set()

# The tree is laid out for a plugin rooted at `claude-code/`, so `../../docs`
# resolves inside the plugin. This fork keeps the skills in a shared
# `skills/` directory beside `pstack/`, one level higher, so those links gain
# the `pstack/` segment. PORT.md documents why.
LINK_RULES = [
    ("](../../docs/", "](../../pstack/docs/"),
    ("](../../README.md)", "](../../pstack/README.md)"),
    ("](../../skills/", "](../../../skills/"),
    ("](./02-poteto-mode.md", "](./02-tomato-mode.md"),
    ("](./skills/", "](../skills/"),
    (
        "When you tell the user to type it, write `/pstack:<name>`.",
        "When you tell the user to type it, write `/<name>`, because this repo loads the skills "
        "from `~/.agents/skills` and nothing prefixes them.",
    ),
    (
        "| `poteto-agent`, `comment-sicko` | `pstack:poteto-agent`, `pstack:comment-sicko` |",
        "| `poteto-agent`, `comment-sicko` | `poteto-agent`, `comment-sicko`. This repo loads "
        "them as plain agent prompts in `pstack/agents/`, so no plugin prefix applies. |",
    ),
]

# The generated tree points at the adapter from every skill that carries Cursor
# names. This fork states the port once, in the same place, and spells out that
# the adapter maps to Claude Code rather than away from it.
ADAPTER_UPSTREAM = (
    "In Claude Code, read [the Claude Code adapter](../../docs/harness/claude-code.md) "
    "once per session before you follow this skill. It maps the Cursor names in pstack skills "
    "to Claude Code."
)
ADAPTER_LOCAL = (
    "This local port runs pstack under Claude Code. Read "
    "[the Claude Code adapter](../../pstack/docs/harness/claude-code.md) once per session "
    "before you follow this skill: it maps every Cursor name in pstack skills to its "
    "Claude Code equivalent."
)


def read_pin():
    pin = {}
    with open(PIN_FILE) as fh:
        for line in fh:
            parts = line.split(None, 1)
            if len(parts) == 2:
                pin[parts[0]] = parts[1].strip()
    return pin


def git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


def fetch(repo_url, ref, dest):
    os.makedirs(dest, exist_ok=True)
    git("init", "-q", cwd=dest)
    git("remote", "add", "origin", repo_url, cwd=dest)
    git("fetch", "-q", "--depth", "1", "origin", ref, cwd=dest)
    git("checkout", "-q", "FETCH_HEAD", cwd=dest)
    return dest


def tree_files(tree, subpath):
    base = os.path.join(tree, subpath)
    out = {}
    for dirpath, _, names in os.walk(base):
        for name in names:
            full = os.path.join(dirpath, name)
            out[os.path.relpath(full, base)] = full
    return out


def local_path(rel):
    rel = FILE_RENAMES.get(rel, rel)
    top, _, rest = rel.partition("/")
    if top == "skills":
        skill, _, tail = rest.partition("/")
        if skill in NOT_INSTALLED:
            return None
        skill = RENAMED.get(skill, skill)
        candidate = os.path.join("skills", skill, tail) if tail else os.path.join("skills", skill)
    elif top == "agents":
        candidate = os.path.join("pstack", "agents", rest)
    elif top == "docs":
        candidate = os.path.join("pstack", "docs", rest)
    elif rel in ("README.md", "LICENSE", "plugin.json"):
        candidate = os.path.join("pstack", rel)
    elif top == ".claude-plugin":
        candidate = os.path.join("pstack", ".claude-plugin", rest)
    else:
        return None
    return None if candidate in DELETED_PATHS else candidate


def transform(rel, data):
    """Upstream bytes for `rel` become the bytes this fork carries."""
    if not rel.endswith((".md", ".mjs", ".ts", ".json", ".sh", ".lock")):
        return data
    text = data.decode("utf-8")
    text = text.replace(ADAPTER_UPSTREAM, ADAPTER_LOCAL)
    for upstream, local in LINK_RULES:
        text = text.replace(upstream, local)
    text = re.sub(r"poteto-mode-tools", "tomato-mode-tools", text)
    text = re.sub(r"poteto-mode", "tomato-mode", text)
    text = re.sub(r"poteto-help", "tomato-help", text)
    text = re.sub(r"poteto-agent", "tomato-agent", text)
    text = re.sub(r"Poteto mode", "Tomato mode", text)
    text = re.sub(r"Poteto help", "Tomato help", text)
    text = re.sub(r"poteto", "tomato", text)
    text = re.sub(r"Poteto", "Tomato", text)
    return text.encode("utf-8")


def read(path):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default=None, help="upstream commit or branch to compare against")
    ap.add_argument("--diffs", action="store_true", help="print diffs for REVIEW files")
    args = ap.parse_args()

    pin = read_pin()
    head_ref = args.ref or "HEAD"
    work = tempfile.mkdtemp(prefix="pstack-upstream-")
    try:
        base_tree = fetch(pin["repo"], pin["commit"], os.path.join(work, "base"))
        head_tree = fetch(pin["repo"], head_ref, os.path.join(work, "head"))
        head_sha = git("rev-parse", "HEAD", cwd=head_tree).strip()

        base_files = tree_files(base_tree, TREE)
        head_files = tree_files(head_tree, TREE)

        print(f"baseline {pin['commit'][:12]} ({pin.get('version', '?')})  ->  upstream {head_sha[:12]}")
        if head_sha == pin["commit"]:
            print("upstream is unchanged since the pin. Nothing to do.")
            return 0

        buckets = {"REVIEW": [], "TAKE": [], "NEW": [], "GONE": [], "SKIPPED": []}

        for rel, head_full in sorted(head_files.items()):
            base_full = base_files.get(rel)
            head_bytes = read(head_full)
            base_bytes = read(base_full) if base_full else None

            if base_bytes is not None and base_bytes == head_bytes:
                continue

            mapped = local_path(rel)
            if mapped is None:
                buckets["SKIPPED"].append(rel)
                continue
            if base_bytes is None:
                buckets["NEW"].append((rel, mapped))
                continue

            local_bytes = read(os.path.join(REPO, mapped))
            if local_bytes is None:
                buckets["NEW"].append((rel, mapped))
            elif local_bytes == transform(rel, base_bytes):
                buckets["TAKE"].append((rel, mapped))
            else:
                buckets["REVIEW"].append((rel, mapped, base_full, head_full))

        for rel in sorted(set(base_files) - set(head_files)):
            mapped = local_path(rel)
            if mapped and read(os.path.join(REPO, mapped)) is not None:
                buckets["GONE"].append((rel, mapped))

        order = ["REVIEW", "TAKE", "NEW", "GONE", "SKIPPED"]
        total = sum(len(buckets[k]) for k in order)
        print(f"{total} upstream change(s) affecting this port\n")
        for key in order:
            items = buckets[key]
            if not items:
                continue
            print(f"{key} ({len(items)})")
            for item in items:
                print(f"  {item[1] if isinstance(item, tuple) else item}")
            print()

        if args.diffs and buckets["REVIEW"]:
            for rel, mapped, base_full, head_full in buckets["REVIEW"]:
                print(f"===== {mapped}")
                print("--- upstream change since baseline")
                subprocess.run(["diff", "-u", base_full, head_full])
                print("--- our change since baseline")
                local_copy = os.path.join(work, "local-transform")
                with open(local_copy, "wb") as fh:
                    fh.write(transform(rel, read(base_full)))
                subprocess.run(["diff", "-u", local_copy, os.path.join(REPO, mapped)])
                print()

        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
