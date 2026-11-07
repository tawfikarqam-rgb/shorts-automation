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

    def test_reject_non_object_json(self):
        with self.assertRaises(ValueError):
            module.parse_object('["no"]')

    def test_extract_text(self):
        data = {"candidates": [{"content": {"parts": [{"text": '{"x":1}'}]}}]}
        self.assertEqual(module.extract_text(data), '{"x":1}')

    def test_reject_empty_text(self):
        with self.assertRaises(ValueError):
            module.extract_text({"candidates": [{"content": {"parts": []}}]})

    def test_extract_only_grounded_https_sources(self):
        data = {"candidates": [{"groundingMetadata": {"groundingChunks": [
            {"web": {"uri": "https://search.example/redirect/1", "title": "Archive"}},
            {"web": {"uri": "https://museum.example/item", "title": "Museum"}},
            {"web": {"uri": "http://unsafe.example/item", "title": "Unsafe"}},
            {"web": {"uri": "https://museum.example/item", "title": "Duplicate"}},
            {"retrievedContext": {"uri": "https://not-a-web-source.example"}},
        ]}}]}
        sources = module.extract_grounded_sources(data)
        self.assertEqual(len(sources), 2)
        self.assertEqual(len(module.validate_sources(sources)), 2)

    def test_reject_fewer_than_two_grounded_sources(self):
        with self.assertRaises(ValueError):
            module.validate_sources([{"url": "https://one.example/story"}])

    def test_duplicate_topic_is_rejected(self):
        self.assertTrue(module.matches_used_topic(
            "The Fake Fossil That Fooled Scientists",
            ["The Fake Fossil That Fooled Scientists"],
        ))

    @patch.object(module.requests, "post")
    def test_google_search_request_uses_gemini_endpoint_and_header(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]
        }
        post.return_value = response
        raw, _ = module.gemini_generate(
            "test-secret", "gemini-3.8-flash", "research",
            google_search=True,
        )
        self.assertEqual(raw, '{"ok":true}')
        self.assertIn("/models/gemini-3.8-flash:generateContent", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["json"]["tools"], [{"google_search": {}}])
        self.assertEqual(post.call_args.kwargs["headers"]["x-goog-api-key"], "test-secret")
        self.assertNotIn("test-secret", post.call_args.args[0])

    @patch.object(module.requests, "post")
    def test_json_writer_request(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]
        }
        post.return_value = response
        module.gemini_generate("test-secret", "gemini-3.8-flash", "write", json_mode=True)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
        self.assertNotIn("tools", payload)

    @patch.object(module.time, "sleep")
    @patch.object(module.requests, "post")
    def test_retries_transient_server_error(self, post, sleep):
        failed = Mock()
        failed.status_code = 503
        failed.ok = False
        failed.text = "temporary failure"
        failed.reason = "Unavailable"
        succeeded = Mock()
        succeeded.status_code = 200
        succeeded.ok = True
        succeeded.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"ok":true}'}]}}]
        }
        post.side_effect = [failed, succeeded]
        raw, _ = module.gemini_generate("test-secret", "gemini-3.8-flash", "research")
        self.assertEqual(raw, '{"ok":true}')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(5)

    def test_research_prompt_requires_grounded_evidence(self):
        prompt = module.build_research_prompt("history", "", "", ["Used topic"])
        self.assertIn("Google Search grounding", prompt)
        self.assertIn("at least 3 specific supported factual claims", prompt)
        self.assertIn("Do not include a sources array", prompt)

    def test_writer_prompt_uses_grounded_sources(self):
        sources = [
            {"title": "Source A", "url": "https://a.example/story", "publisher": "a.example"},
            {"title": "Source B", "url": "https://b.example/story", "publisher": "b.example"},
        ]
        prompt = module.build_writer_prompt(
            "history", "A verified story", ["Fact 1"], ["Disputed"], sources
        )
        self.assertIn("https://a.example/story", prompt)
        self.assertIn("https://b.example/story", prompt)
        self.assertIn("Use only these verified facts", prompt)


if __name__ == "__main__":
    unittest.main()
