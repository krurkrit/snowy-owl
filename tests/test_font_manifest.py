"""Validate the pinned, optional font-download manifest."""

import json
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class FontManifestTests(unittest.TestCase):
    """Keep downloadable files aligned with typography preferences."""

    def setUp(self):
        """Load the font manifest and global typography document."""
        self.manifest = json.loads(
            (ROOT / "fonts" / "manifest.json").read_text(encoding="utf-8")
        )
        self.typography = yaml.safe_load(
            (ROOT / "tokens" / "typography.yaml").read_text(encoding="utf-8")
        )

    def test_sources_are_pinned_and_checksummed(self):
        """Require immutable source URLs and valid SHA-256 values."""
        revision = self.manifest["source"]["revision"]
        self.assertRegex(revision, r"^[0-9a-f]{40}$")
        for font in self.manifest["fonts"]:
            self.assertIn(revision, font["licenseUrl"])
            for file in font["files"]:
                self.assertIn(revision, file["url"])
                self.assertEqual("https", file["url"].split(":", 1)[0])
                self.assertRegex(file["sha256"], r"^[0-9a-f]{64}$")

    def test_downloads_cover_preferred_font_styles(self):
        """Cover every declared style for each downloadable family."""
        downloads = {
            font["family"]: {
                style for file in font["files"] for style in file["styles"]
            }
            for font in self.manifest["fonts"]
        }
        for role in ("ui", "monospace"):
            for font in self.typography[role]["fonts"]:
                if font["family"] in downloads:
                    self.assertEqual(set(font["styles"]), downloads[font["family"]])

    def test_destination_names_are_unique_and_safe(self):
        """Prevent collisions or paths outside the user font directory."""
        names = [
            file["fileName"]
            for font in self.manifest["fonts"]
            for file in font["files"]
        ]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertEqual(name, Path(name).name)
            self.assertRegex(name, r"^[A-Za-z0-9._-]+$")


if __name__ == "__main__":
    unittest.main()
