import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.create_thumbnail import choose_source, create_thumbnail, wrap_headline


class ThumbnailTests(unittest.TestCase):
    def test_thumbnail_is_vertical_jpeg(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.png"
            output = root / "thumbnail.jpg"
            Image.new("RGB", (1200, 900), (35, 65, 95)).save(source)
            create_thumbnail(source, output, "The Company That Lost Its Crown", "business")
            with Image.open(output) as result:
                self.assertEqual(result.format, "JPEG")
                self.assertEqual(result.size, (1080, 1920))
            self.assertGreater(output.stat().st_size, 1000)

    def test_choose_source_prefers_cloudflare_image(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            licensed = root / "scene_1.jpg"
            generated = root / "cloudflare_scene_1.jpg"
            licensed.write_bytes(b"x" * 12000)
            generated.write_bytes(b"y" * 12000)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps([str(licensed), str(generated)]), encoding="utf-8")
            self.assertEqual(choose_source(manifest), generated)

    def test_headline_is_limited_to_three_lines(self):
        image = Image.new("RGB", (1080, 1920), "black")
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 88)
        lines = wrap_headline(draw, "A very long headline that should be shortened to fit within three clear readable lines on the thumbnail", font, 930)
        self.assertLessEqual(len(lines), 3)


if __name__ == "__main__":
    unittest.main()
