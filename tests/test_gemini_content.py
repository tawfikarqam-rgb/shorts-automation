import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1] / "scripts" / "gemini_content.py"
spec = importlib.util.spec_from_file_location("gemini_content", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GeminiContentTests(unittest.TestCase):
    def test_parse_json_object(self):
        self.assertEqual(module.parse_object('{"ok": true}'), {"ok": True})

    def test_parse_fenced_json(self):
        raw = chr(96) * 3 + "json\n" + '{"ok": true}' + "\n" + chr(96) * 3
        self.assertEqual(module.parse_object(raw), {"ok": True})

    def test_reject_non_object_json(self):
        with self.assertRaises(ValueError):
            module.parse_object('["not an object"]')

    def test_extract_text(self):
        data = {"candidates": [{"content": {"parts": [{"text": '{"topic":"x"}'}]}}]}
        self.assertEqual(module.extract_text(data), '{"topic":"x"}')

    def test_reject_empty_candidate(self):
        with self.assertRaises(ValueError):
            module.extract_text({"candidates": [{"content": {"parts": []}}]})

    def test_grounding_requires_multiple_sources_queries_and_supports(self):
        data = {"candidates": [{
            "groundingMetadata": {
                "webSearchQueries": ["test query"],
                "groundingChunks": [
                    {"web": {"uri": "https://source-one.example/a", "title": "One"}},
                    {"web": {"uri": "https://source-two.example/b", "title": "Two"}},
                ],
                "groundingSupports": [{"segment": {"text": "claim"}, "groundingChunkIndices": [0]}],
            }
        }]}
        sources, metadata = module.validate_grounding(data)
        self.assertEqual(len(sources), 2)
        self.assertEqual(metadata["webSearchQueries"], ["test query"])

    def test_reject_missing_grounding(self):
        with self.assertRaises(ValueError):
            module.validate_grounding({"candidates": [{"groundingMetadata": {}}]})

    def test_duplicate_topic_is_rejected(self):
        self.assertTrue(module.matches_used_topic(
            "The Fake Fossil That Fooled Scientists",
            ["The Fake Fossil That Fooled Scientists"],
        ))

    @patch.object(module.requests, "post")
    def test_gemini_request_uses_secret_header_and_google_search(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]
        }
        post.return_value = response

        raw, data = module.gemini_generate("test-secret", "gemini-3.8-flash", "research", True)

        self.assertEqual(raw, '{"ok":true}')
        self.assertIn("x-goog-api-key", post.call_args.kwargs["headers"])
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-secret")
        self.assertEqual(post.call_args.kwargs["json"]["tools"], [{"google_search": {}}])
        self.assertNotIn("test-secret", post.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
