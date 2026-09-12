import unittest
import tempfile
from pathlib import Path

from scripts.token_resolver import (
    TokenHeaderError,
    TokenReferenceError,
    load_token_documents,
    load_token_documents_from_paths,
    load_token_header,
    load_token_metadata,
    load_yaml,
    resolve_documents,
    resolve_references,
)

ROOT = Path(__file__).resolve().parents[1]


class TokenResolverTests(unittest.TestCase):
    def test_project_tokens_resolve(self):
        tokens = load_token_documents(ROOT / "tokens")

        self.assertEqual(tokens["colors"]["light"]["background"], "#F8F9FA")
        self.assertEqual(
            tokens["contrast-rules"]["rules"][0]["foreground"],
            "#34383C",
        )

    def test_project_token_headers_drive_report_metadata(self):
        metadata = {
            document["namespace"]: document
            for document in load_token_metadata(ROOT / "tokens")
        }

        self.assertEqual(set(metadata), {"colors", "contrast-rules", "typography"})
        self.assertEqual(metadata["colors"]["name"], "Colors")
        self.assertEqual(metadata["colors"]["type"], "color")
        self.assertIsInstance(metadata["colors"]["hierarchy"], int)
        self.assertEqual(metadata["contrast-rules"]["type"], "contrast-rules")
        self.assertEqual(metadata["typography"]["type"], "typography")

    def test_invalid_token_header_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            path.write_text("---\nvalue: true\n", encoding="utf-8")
            with self.assertRaises(TokenHeaderError):
                load_token_header(path)

    def test_hierarchy_defaults_to_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "colors.yaml"
            path.write_text(
                "snowyOwl:\n  name: Colors\n  type: color\nvalue: true\n",
                encoding="utf-8",
            )

            self.assertEqual(load_token_header(path)["hierarchy"], 0)

    def test_app_mappings_resolve(self):
        for path in (ROOT / "apps").glob("*/mapping.yaml"):
            with self.subTest(path=path):
                tokens = load_token_documents(ROOT / "tokens", [path.parent])
                resolve_references(load_yaml(path), tokens)

    def test_reference_preserves_value_type(self):
        resolved = resolve_documents(
            {
                "source": {"fallback": ["Inter", "sans-serif"]},
                "consumer": {"fallback": "{source.fallback}"},
            }
        )

        self.assertEqual(resolved["consumer"]["fallback"], ["Inter", "sans-serif"])

    def test_higher_hierarchy_overrides_lower_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n"
                "light:\n  background: '#FFFFFF'\n",
                encoding="utf-8",
            )
            (root / "colors.override.yaml").write_text(
                "snowyOwl:\n  name: Override Colors\n  type: color\n  hierarchy: 1\n"
                "light:\n  background: '#FDFDFD'\n",
                encoding="utf-8",
            )

            tokens = load_token_documents(root)

            self.assertEqual(tokens["colors"]["light"]["background"], "#FDFDFD")
            self.assertEqual(load_token_metadata(root)[0]["hierarchy"], 1)
            self.assertEqual(
                load_token_documents_from_paths([root / "colors.yaml"])["colors"]
                ["light"]["background"],
                "#FFFFFF",
            )

    def test_app_local_layer_only_overrides_that_app(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_directory = root / "tokens"
            app_directory = root / "apps" / "sample"
            token_directory.mkdir(parents=True)
            app_directory.mkdir(parents=True)
            (token_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n"
                "light:\n  background: '#FFFFFF'\n",
                encoding="utf-8",
            )
            (app_directory / "colors.override.yaml").write_text(
                "snowyOwl:\n  name: App Colors\n  type: color\n  hierarchy: 2\n"
                "light:\n  background: '#EEEEEE'\n",
                encoding="utf-8",
            )

            global_tokens = load_token_documents(token_directory)
            app_tokens = load_token_documents(token_directory, [app_directory])

            self.assertEqual(global_tokens["colors"]["light"]["background"], "#FFFFFF")
            self.assertEqual(app_tokens["colors"]["light"]["background"], "#EEEEEE")

    def test_app_hierarchy_is_independent_from_global_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_directory = root / "tokens"
            app_directory = root / "apps" / "sample"
            token_directory.mkdir(parents=True)
            app_directory.mkdir(parents=True)
            (token_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 1\n"
                "dark:\n  background: '#18191B'\n",
                encoding="utf-8",
            )
            (app_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 1\n"
                "dark:\n  background: '#18191A'\n",
                encoding="utf-8",
            )

            tokens = load_token_documents(token_directory, [app_directory])

            self.assertEqual(tokens["colors"]["dark"]["background"], "#18191A")

    def test_same_hierarchy_still_conflicts_inside_app_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_directory = root / "tokens"
            app_directory = root / "apps" / "sample"
            token_directory.mkdir(parents=True)
            app_directory.mkdir(parents=True)
            (token_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n"
                "dark:\n  background: '#18191B'\n",
                encoding="utf-8",
            )
            for filename, value in (
                ("colors.first.yaml", "#18191A"),
                ("colors.second.yaml", "#181919"),
            ):
                (app_directory / filename).write_text(
                    "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 1\n"
                    f"dark:\n  background: '{value}'\n",
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(TokenHeaderError, "hierarchy 1"):
                load_token_documents(token_directory, [app_directory])

    def test_override_extends_project_token_data(self):
        with tempfile.TemporaryDirectory() as directory:
            override_directory = Path(directory)
            (override_directory / "colors.override.yaml").write_text(
                "snowyOwl:\n"
                "  name: Extended Colors\n"
                "  type: color\n"
                "  hierarchy: 1\n"
                "light:\n"
                "  background: '#FDFDFD'\n"
                "  customSurface: '#ECEFF1'\n",
                encoding="utf-8",
            )

            original = load_token_documents(ROOT / "tokens")
            extended = load_token_documents(
                ROOT / "tokens", [override_directory]
            )

            self.assertEqual(original["colors"]["light"]["background"], "#F8F9FA")
            self.assertEqual(extended["colors"]["light"]["background"], "#FDFDFD")
            self.assertEqual(extended["colors"]["light"]["customSurface"], "#ECEFF1")
            self.assertEqual(
                extended["colors"]["light"]["foreground"],
                original["colors"]["light"]["foreground"],
            )

    def test_conflicting_values_at_same_hierarchy_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, value in (("colors.yaml", "#FFFFFF"), ("colors.alt.yaml", "#EEEEEE")):
                (root / filename).write_text(
                    "snowyOwl:\n  name: Colors\n  type: color\n"
                    f"light:\n  background: '{value}'\n",
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(
                TokenHeaderError, r"colors\.light\.background.*hierarchy 0"
            ):
                load_token_documents(root)

    def test_missing_reference_fails(self):
        with self.assertRaisesRegex(TokenReferenceError, "Unknown token reference"):
            resolve_documents({"consumer": {"value": "{missing.value}"}})

    def test_cycle_fails(self):
        with self.assertRaisesRegex(TokenReferenceError, "Cyclic token reference"):
            resolve_documents(
                {
                    "first": {"value": "{second.value}"},
                    "second": {"value": "{first.value}"},
                }
            )


if __name__ == "__main__":
    unittest.main()
