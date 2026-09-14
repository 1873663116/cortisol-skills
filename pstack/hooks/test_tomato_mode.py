import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HOOK = Path(__file__).with_name("tomato_mode.py")


class TomatoModeHookTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.TemporaryDirectory()
        self.addCleanup(self.home.cleanup)
        self.env = {**os.environ, "HOME": self.home.name}
        self.state_dir = Path(self.home.name) / ".cache" / "tomato-mode"

    def run_raw(self, raw):
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=raw,
            text=True,
            capture_output=True,
            env=self.env,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        return result.stdout

    def submit(self, prompt, session_id="session-a"):
        return self.run_raw(json.dumps({
            "session_id": session_id,
            "prompt": prompt,
            "hook_event_name": "UserPromptSubmit",
        }))

    def activate(self, prompt="/tomato-mode", session_id="session-a"):
        output = self.submit(prompt, session_id)
        self.assertIn("Tomato mode is now on for this session.", output)
        self.assertEqual((self.state_dir / session_id).read_text(), session_id)

    def test_activation(self):
        self.assertEqual(self.submit("Review this change."), "")
        self.activate()

    def test_reminder_on_next_turn(self):
        self.activate()
        self.assertIn("Tomato mode is on.", self.submit("Continue."))

    def test_off_clears_session_and_stops_reminders(self):
        for token in ("/tomato-off", "$tomato-off"):
            with self.subTest(token=token):
                self.activate()
                self.assertEqual(self.submit(token), "")
                self.assertFalse((self.state_dir / "session-a").exists())
                self.assertEqual(self.submit("Continue."), "")

    def test_sessions_are_isolated(self):
        self.activate()
        self.assertEqual(self.submit("Continue.", "session-b"), "")
        self.assertEqual(self.submit("/tomato-off", "session-b"), "")
        self.assertIn("Tomato mode is on.", self.submit("Continue."))

    def test_code_tokens_do_not_activate(self):
        for prompt in (
            "Explain `/tomato-mode`.",
            "Explain `$tomato-mode`.",
            "```text\n/tomato-mode\n```",
            "```text\n$tomato-mode\n```",
        ):
            with self.subTest(prompt=prompt):
                self.assertEqual(self.submit(prompt), "")
                self.assertFalse((self.state_dir / "session-a").exists())
        self.activate()

    def test_codex_markdown_skill_link_activates(self):
        self.activate(
            "[$tomato-mode](/Users/example/.agents/skills/tomato-mode/SKILL.md)"
        )
        self.assertIn("Tomato mode is on.", self.submit("Continue."))

    def test_invalid_json_is_silent_and_preserves_active_session(self):
        self.activate()
        for raw in ("", "not json", '{"prompt":'):
            with self.subTest(raw=raw):
                self.assertEqual(self.run_raw(raw), "")
        self.assertIn("Tomato mode is on.", self.submit("Continue."))


if __name__ == "__main__":
    unittest.main()
