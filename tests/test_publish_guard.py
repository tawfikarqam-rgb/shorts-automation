import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_guard.py"
SPEC = importlib.util.spec_from_file_location("publish_guard", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublishGuardTests(unittest.TestCase):
    def test_blocks_legacy_topic(self):
        ledger = {"legacy_blocked_topics": ["The Fake Fossil That Fooled Scientists"], "entries": []}
        self.assertIsNotNone(MODULE.find_duplicate(
            "The Fake Fossil That Fooled Scientists", "A new narration.", "abc", ledger
        ))

    def test_blocks_same_narration_with_changed_title(self):
        old = "A company changed its product and customers strongly objected to the decision."
        ledger = {"legacy_blocked_topics": [], "entries": [{"topic": "Old title", "script": old}]}
        self.assertEqual(
            MODULE.find_duplicate("Different title", old, "new-file-hash", ledger),
            "narration matches a previously reserved/published script",
        )

    def test_blocks_identical_video_hash(self):
        ledger = {"legacy_blocked_topics": [], "entries": [{"topic": "Old", "script": "Old script", "video_sha256": "same"}]}
        self.assertEqual(
            MODULE.find_duplicate("New", "New script", "same", ledger),
            "identical final MP4 SHA-256",
        )

    def test_allows_new_story(self):
        ledger = {"legacy_blocked_topics": ["The Fake Fossil That Fooled Scientists"], "entries": []}
        self.assertIsNone(MODULE.find_duplicate(
            "A New Story About Space Exploration", "A completely different narration about a new subject.", "different", ledger
        ))


if __name__ == "__main__":
    unittest.main()
