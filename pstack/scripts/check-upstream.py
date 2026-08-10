#!/usr/bin/env python3
"""Report what changed in upstream pstack since the pinned baseline.

Splits every upstream change by whether this fork has touched that file, which
is the only question that decides how much judgment the update needs:

  TAKE    upstream changed it, we never did. Copy it over, re-apply the
          mechanical rules in PORT.md, done.
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
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
PIN_FILE = os.path.join(ROOT, "UPSTREAM")

# Upstream lays skills out under pstack/skills/<name>. This fork hoists them to
# skills/<name> so every harness that scans a skills directory finds them, with
# the exceptions below. Keep this table and PORT.md in step.
RENAMED = {"tdd": "tdd-bug-fix"}
NOT_INSTALLED = {"setup-pstack"}
DELETED_PATHS = {
    "skills/poteto-mode/playbooks/autopilot-stack.md",
    "skills/poteto-mode/playbooks/orchestrate.md",
}


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


def upstream_files(tree, subpath):
    base = os.path.join(tree, subpath, "skills")
    out = {}
    for dirpath, _, names in os.walk(base):
        for name in names:
            full = os.path.join(dirpath, name)
            out[os.path.relpath(full, base)] = full
    return out


def local_path(rel):
    skill = rel.split(os.sep, 1)[0]
    if skill in NOT_INSTALLED:
        return None
    rest = rel.split(os.sep, 1)[1] if os.sep in rel else ""
    mapped = RENAMED.get(skill, skill)
    candidate = os.path.join("skills", mapped, rest) if rest else os.path.join("skills", mapped)
    return None if candidate in DELETED_PATHS else candidate


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

        base_files = upstream_files(base_tree, pin["path"])
        head_files = upstream_files(head_tree, pin["path"])

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
            elif local_bytes == base_bytes:
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
                subprocess.run(["diff", "-u", base_full, os.path.join(REPO, mapped)])
                print()

        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
