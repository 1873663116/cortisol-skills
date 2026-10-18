# Tomato mode hook

Claude Code and Codex use `tomato_mode.py` for `UserPromptSubmit`. The script reads `session_id` and `prompt` from JSON on stdin and emits the activation message or reminder on stdout.

`/tomato-mode` or `$tomato-mode` enables reminders for the session. `/tomato-off` or `$tomato-off` disables them. Tokens inside backticks or fenced code blocks are ignored.

## Codex registration

Merge `codex-hooks.json` into `~/.codex/hooks.json`, retaining existing handlers. Set `hooks = true` under `[features]` in `~/.codex/config.toml`.

Start a new Codex session and use `/hooks` to review and trust the registered command. Codex skips new or changed hook definitions until trusted. See the [official hook documentation](https://learn.chatgpt.com/docs/hooks).

Run `python3 -m unittest discover -s pstack/hooks -p 'test_*.py'` from the repository root to verify activation, reminders, shutdown, session isolation, and prompt parsing.
