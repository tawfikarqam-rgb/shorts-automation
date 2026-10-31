import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "collect_youtube_analytics.py"


class AnalyticsCollectorTests(unittest.TestCase):
    def test_missing_credentials_skip_cleanly(self):
        env = os.environ.copy()
        for key in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_ANALYTICS_REFRESH_TOKEN"):
            env.pop(key, None)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--channel", "business"],
            env=env, capture_output=True, text=True, check=True,
        )
        self.assertIn("ANALYTICS_SKIPPED", result.stdout)

    def test_invalid_window_fails_before_network(self):
        env = os.environ.copy()
        env["YOUTUBE_CLIENT_ID"] = "x"
        env["YOUTUBE_CLIENT_SECRET"] = "x"
        env["YOUTUBE_ANALYTICS_REFRESH_TOKEN"] = "x"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--channel", "business", "--days", "2"],
            env=env, capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--days must be between 7 and 90", result.stderr)


if __name__ == "__main__":
    unittest.main()
