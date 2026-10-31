import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "oxion_content.py"
spec = importlib.util.spec_from_file_location("oxion_content", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OxionContentTests(unittest.TestCase):
    def test_json_object(self):
        self.assertEqual(module.parse_object('{"ok":true}'), {"ok": True})

    def test_fenced_json(self):
        self.assertEqual(module.parse_object(chr(96)*3 + 'json' + chr(10) + '{"ok":true}' + chr(10) + chr(96)*3), {"ok": True})

    def test_reject_array(self):
        with self.assertRaises(ValueError):
            module.parse_object('["not an object"]')


if __name__ == "__main__":
    unittest.main()
