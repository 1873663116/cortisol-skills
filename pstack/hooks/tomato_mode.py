#!/usr/bin/env python3
"""UserPromptSubmit hook that makes tomato mode sticky across turns.

A skill's SKILL.md enters context only on the turn it is invoked. Nothing
re-asserts its routing rule afterwards, so within a few turns the mode has
drifted out of attention. This hook re-injects one line of routing rule beside
the current user message on every turn the mode is on.

Registered against UserPromptSubmit with matcher "*", so it runs on every turn
of every session. What varies is the output, driven by a per-session state file:

  prompt contains /tomato-off or $tomato-off   -> clear state, emit nothing
  prompt contains /tomato-mode or $tomato-mode -> set state, emit activation
  state set                                    -> emit the reminder
  otherwise                                    -> emit nothing

Both sigils are accepted because harnesses disagree: Claude Code submits
/tomato-mode, T3 Code rewrites the same keystroke to $tomato-mode.

The activation line points at the SKILL.md by path. A harness expands
/tomato-mode into the full SKILL.md only when it recognises it as a leading
slash command; a mid-message mention, or any $-sigil form, arrives as bare
text, and the skill's disable-model-invocation marker keeps it out of the
model's skill listing, so without this line the model would see the token,
find no such skill, and ignore it while the state file silently flips on.
When the harness did expand the command, the extra line is harmless.

The hook runs before the harness expands a slash command, so it reads the text
as typed. Occurrences inside backticks or fenced code blocks are ignored, so
discussing the command does not activate it.

`--debug on` appends every raw stdin payload to payloads.log, which is how you
find out what a given harness actually sends.
"""

import json
import os
import re
import sys
import time

STATE_DIR = os.path.expanduser("~/.cache/tomato-mode")
DEBUG_MARKER = os.path.join(STATE_DIR, ".debug")
PAYLOAD_LOG = os.path.join(STATE_DIR, "payloads.log")
LOG_NAME = os.path.basename(PAYLOAD_LOG)
REMINDER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reminder.txt")
SKILL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "skills", "tomato-mode", "SKILL.md",
)

# A state file this old belongs to a session that ended without SessionEnd
# firing. SessionEnd's trigger conditions are undocumented, so correctness must
# not depend on it; this prune is what actually bounds the directory.
STALE_AFTER_SECONDS = 24 * 60 * 60

FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`]*`")


def _token(name):
    # Harnesses disagree on the sigil. Claude Code submits /tomato-mode; T3
    # Code rewrites the same keystroke to $tomato-mode. Match either, so the
    # mode turns on wherever the hook is registered.
    #
    # Neither `/` nor `$` is a word character, so \b does not work on the left.
    # Reject a preceding word char, sigil or dash so a/tomato-mode does not
    # match, and reject a trailing word char or dash so /tomato-modes does not.
    return re.compile(
        r"(?<![\w/$-])[/$]" + re.escape(name) + r"(?![\w-])", re.IGNORECASE
    )


OFF_TOKEN = _token("tomato-off")
ON_TOKEN = _token("tomato-mode")


def strip_code(text):
    return INLINE_CODE.sub(" ", FENCED_CODE.sub(" ", text))


def state_path(session_id):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id) or "unknown"
    return os.path.join(STATE_DIR, safe)


def session_files():
    try:
        names = os.listdir(STATE_DIR)
    except OSError:
        return []
    return [n for n in names if not n.startswith(".") and n != LOG_NAME]


def prune_stale():
    cutoff = time.time() - STALE_AFTER_SECONDS
    for name in session_files():
        path = os.path.join(STATE_DIR, name)
        try:
            if os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            pass


def log_payload(raw):
    if not os.path.exists(DEBUG_MARKER):
        return
    try:
        with open(PAYLOAD_LOG, "a") as fh:
            fh.write(f"--- {time.strftime('%Y-%m-%d %H:%M:%S')}\n{raw}\n")
    except OSError:
        pass


def cmd_status():
    print(f"state dir: {STATE_DIR}")
    print(f"debug logging: {'on' if os.path.exists(DEBUG_MARKER) else 'off'}")
    names = sorted(session_files())
    print(f"active sessions: {len(names)}")
    for name in names:
        age = int(time.time() - os.path.getmtime(os.path.join(STATE_DIR, name)))
        print(f"  {name}  (touched {age}s ago)")
    return 0


def cmd_debug(value):
    os.makedirs(STATE_DIR, exist_ok=True)
    if value == "on":
        open(DEBUG_MARKER, "w").close()
        print(f"payload logging on -> {PAYLOAD_LOG}")
    else:
        try:
            os.unlink(DEBUG_MARKER)
        except OSError:
            pass
        print("payload logging off")
    return 0


def run_hook():
    raw = sys.stdin.read()
    log_payload(raw)
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return 0

    session_id = str(payload.get("session_id") or "")
    prompt = strip_code(str(payload.get("prompt") or ""))
    path = state_path(session_id)

    os.makedirs(STATE_DIR, exist_ok=True)
    prune_stale()

    if OFF_TOKEN.search(prompt):
        try:
            os.unlink(path)
        except OSError:
            pass
        return 0

    if ON_TOKEN.search(prompt):
        with open(path, "w") as fh:
            fh.write(session_id)
        sys.stdout.write(
            "Tomato mode is now on for this session. If this turn does not "
            f"already contain the tomato-mode skill, read {SKILL_FILE} in "
            "full before doing anything else.\n"
        )
        return 0

    if not os.path.exists(path):
        return 0

    os.utime(path, None)
    try:
        with open(REMINDER_FILE) as fh:
            sys.stdout.write(fh.read().strip() + "\n")
    except OSError:
        pass
    return 0


def main():
    args = sys.argv[1:]
    if "--status" in args:
        return cmd_status()
    if "--debug" in args:
        i = args.index("--debug")
        return cmd_debug(args[i + 1] if i + 1 < len(args) else "on")
    return run_hook()


if __name__ == "__main__":
    sys.exit(main())
