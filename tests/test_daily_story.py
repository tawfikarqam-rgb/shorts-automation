import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "daily_story.py"
SOURCE = SCRIPT.read_text(encoding="utf-8")


def story_titles_for(channel):
    tree = ast.parse(SOURCE)
    titles = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == channel
            for target in node.targets
        ) and isinstance(node.value, ast.List):
            titles.extend(
                item.elts[0].value
                for item in node.value.elts
                if isinstance(item, ast.Tuple)
                and item.elts
                and isinstance(item.elts[0], ast.Constant)
                and isinstance(item.elts[0].value, str)
            )
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if (
                isinstance(call.func, ast.Attribute)
                and isinstance(call.func.value, ast.Name)
                and call.func.value.id == channel
                and call.func.attr == "extend"
                and call.args
                and isinstance(call.args[0], ast.List)
            ):
                titles.extend(
                    item.elts[0].value
                    for item in call.args[0].elts
                    if isinstance(item, ast.Tuple)
                    and item.elts
                    and isinstance(item.elts[0], ast.Constant)
                    and isinstance(item.elts[0].value, str)
                )
    return titles


class DailyStoryTests(unittest.TestCase):
    def run_selector(self, channel, ledger=None):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        workdir = Path(temp.name)
        env_file = workdir / "github_env.txt"
        env = os.environ.copy()
        env.pop("GITHUB_RUN_NUMBER", None)
        env["CHANNEL_NAME"] = channel
        env["GITHUB_ENV"] = str(env_file)

        ledger_dir = workdir / "state" / "published"
        ledger_dir.mkdir(parents=True)
        if ledger is not None:
            (ledger_dir / f"{channel}.json").write_text(
                json.dumps(ledger), encoding="utf-8"
            )

        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=workdir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        env_text = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        return result, env_text

    def test_both_channels_have_large_unique_reviewed_pools(self):
        for channel in ("history_stories", "business_stories"):
            titles = story_titles_for(channel)
            self.assertGreaterEqual(len(titles), 45, channel)
            self.assertEqual(len(titles), len(set(titles)), channel)

    def test_selects_a_story_and_exports_required_environment(self):
        for channel in ("history", "business"):
            with self.subTest(channel=channel):
                result, env_text = self.run_selector(channel)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("STORY_TOPIC=", env_text)
                self.assertIn("VIDEO_SCRIPT<<STORY_SCRIPT_EOF", env_text)
                self.assertIn("IMAGE_SEARCHES=", env_text)
                self.assertIn("Today's local topic:", result.stdout)

    def test_skips_a_story_already_in_the_duplicate_ledger(self):
        titles = story_titles_for("business_stories")
        first, first_env = self.run_selector("business")
        self.assertEqual(first.returncode, 0, first.stderr)
        selected = re.search(r"^STORY_TOPIC=(.*)$", first_env, re.M).group(1)

        ledger = {"legacy_blocked_topics": [selected], "entries": []}
        second, second_env = self.run_selector("business", ledger)
        self.assertEqual(second.returncode, 0, second.stderr)
        second_selected = re.search(
            r"^STORY_TOPIC=(.*)$", second_env, re.M
        ).group(1)
        self.assertNotEqual(selected, second_selected)
        self.assertIn(second_selected, titles)

    def test_exhausted_pool_fails_closed_with_actionable_message(self):
        for channel in ("history", "business"):
            titles = story_titles_for(channel + "_stories")
            ledger = {"legacy_blocked_topics": titles, "entries": []}
            result, _ = self.run_selector(channel, ledger)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                f"No unused reviewed local stories remain for channel '{channel}'",
                result.stderr,
            )
            self.assertIn("no AI API fallback is configured", result.stderr)

    def test_invalid_channel_is_rejected(self):
        result, _ = self.run_selector("unknown")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("CHANNEL_NAME must be history or business", result.stderr)


if __name__ == "__main__":
    unittest.main()
