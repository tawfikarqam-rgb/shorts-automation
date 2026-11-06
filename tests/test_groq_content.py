import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PATH = Path(__file__).resolve().parents[1] / "scripts" / "groq_content.py"
spec = importlib.util.spec_from_file_location("groq_content", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GroqContentTests(unittest.TestCase):
    def test_parse_json_object(self):
        self.assertEqual(module.parse_object('{"ok": true}'), {"ok": True})

    def test_reject_non_object_json(self):
        with self.assertRaises(ValueError):
            module.parse_object('["no"]')

    def test_extract_message(self):
        self.assertEqual(module.extract_message({"choices": [{"message": {"content": '{"x":1}'}}]}), '{"x":1}')

    def test_reject_empty_message(self):
        with self.assertRaises(ValueError):
            module.extract_message({"choices": [{"message": {"content": ""}}]})


    def test_extract_annotation_sources(self):
        data = {"choices": [{"message": {"annotations": [
            {"type": "url_citation", "url_citation": {
                "url": "https://archive.example/story", "title": "Archive record"
            }},
            {"type": "url_citation", "url_citation": {
                "url": "https://museum.example/exhibit", "title": "Museum exhibit"
            }},
        ]}}]}
        sources = module.extract_annotation_sources(data)
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["url"], "https://archive.example/story")
        self.assertEqual(len(module.validate_sources(sources)), 2)

    def test_extract_annotation_sources_ignores_missing_urls(self):
        data = {"choices": [{"message": {"annotations": [
            {"type": "url_citation", "url_citation": {"title": "No URL"}}
        ]}}]}
        self.assertEqual(module.extract_annotation_sources(data), [])

    def test_validate_two_distinct_https_sources(self):
        sources = [
            {"title": "A", "url": "https://a.example/x", "supports": ["claim"]},
            {"title": "B", "url": "https://b.example/y", "supports": ["claim"]},
        ]
        self.assertEqual(len(module.validate_sources(sources)), 2)

    def test_reject_one_or_invalid_source(self):
        with self.assertRaises(ValueError):
            module.validate_sources([{"url": "http://a.example"}])

    def test_duplicate_topic_is_rejected(self):
        self.assertTrue(module.matches_used_topic("The Fake Fossil That Fooled Scientists",
                                                  ["The Fake Fossil That Fooled Scientists"]))

    @patch.object(module.requests, "post")
    def test_browser_search_request(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        post.return_value = response
        raw, _ = module.groq_generate("test-secret", "openai/gpt-oss-20b",
            [{"role": "user", "content": "research"}], browser_search=True)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(raw, '{"ok":true}')
        self.assertEqual(payload["tools"], [{"type": "browser_search"}])
        self.assertEqual(payload["tool_choice"], "required")
        self.assertNotIn("test-secret", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer test-secret")

    @patch.object(module.time, "sleep")
    @patch.object(module.requests, "post")
    def test_retries_transient_server_error(self, post, sleep):
        failed = Mock()
        failed.status_code = 500
        failed.ok = False
        failed.text = "temporary server failure"
        failed.headers = {"x-groq-request-id": "req-test"}
        succeeded = Mock()
        succeeded.status_code = 200
        succeeded.ok = True
        succeeded.json.return_value = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        post.side_effect = [failed, succeeded]
        raw, _ = module.groq_generate("test-secret", "openai/gpt-oss-20b",
            [{"role": "user", "content": "research"}], stage="research")
        self.assertEqual(raw, '{"ok":true}')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(5)


    @patch.object(module.time, "sleep")
    @patch.object(module.requests, "post")
    def test_retries_temporary_tpm_limit(self, post, sleep):
        limited = Mock()
        limited.status_code = 429
        limited.ok = False
        limited.text = '{"error":{"message":"Rate limit on tokens per minute. Please try again in 7.74s."}}'
        limited.headers = {}
        succeeded = Mock()
        succeeded.status_code = 200
        succeeded.ok = True
        succeeded.json.return_value = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        post.side_effect = [limited, succeeded]
        raw, _ = module.groq_generate("test-secret", "openai/gpt-oss-20b",
            [{"role": "user", "content": "write"}], stage="writing")
        self.assertEqual(raw, '{"ok":true}')
        self.assertEqual(post.call_count, 2)
        sleep.assert_called_once_with(7.74)

    @patch.object(module.time, "sleep")
    @patch.object(module.requests, "post")
    def test_does_not_retry_daily_token_quota(self, post, sleep):
        limited = Mock()
        limited.status_code = 429
        limited.ok = False
        limited.text = '{"error":{"message":"Limit on tokens per day exceeded. Try again in 7.74s."}}'
        limited.headers = {}
        post.return_value = limited
        with self.assertRaisesRegex(RuntimeError, "HTTP 429"):
            module.groq_generate("test-secret", "openai/gpt-oss-20b",
                [{"role": "user", "content": "write"}], stage="writing")
        self.assertEqual(post.call_count, 1)
        sleep.assert_not_called()

    @patch.object(module.requests, "post")
    def test_json_writer_request(self, post):
        response = Mock()
        response.ok = True
        response.json.return_value = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        post.return_value = response
        module.groq_generate("test-secret", "openai/gpt-oss-20b",
            [{"role": "user", "content": "write"}], json_mode=True)
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"], {"type": "json_object"})
        self.assertNotIn("tools", payload)


if __name__ == "__main__":
    unittest.main()
