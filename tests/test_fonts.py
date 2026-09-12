import unittest

from scripts.font_resolver import FontConfigurationError, resolve_font


TYPOGRAPHY = {
    "monospace": {
        "defaultStyle": "regular",
        "fonts": [
            {
                "family": "Preferred",
                "styles": {
                    "regular": {"weight": 400, "slant": "normal"},
                },
            },
            {
                "family": "Fallback",
                "styles": {
                    "regular": {
                        "weight": 400,
                        "slant": "normal",
                        "fullName": "Fallback Regular",
                        "postScriptName": "Unexpected-Exact-Name",
                    },
                    "medium": {
                        "weight": 500,
                        "slant": "normal",
                        "fullName": "Fallback Medium",
                        "postScriptName": "Fallback-Medium",
                    },
                },
            },
        ],
    }
}


class FontResolverTests(unittest.TestCase):
    def test_uses_first_available_fallback_font_and_style(self):
        result = resolve_font(
            TYPOGRAPHY,
            "monospace",
            {
                "mode": "configuration",
                "style": "medium",
                "requiredProperties": ["fullName", "postScriptName"],
                "availableFonts": [
                    {"family": "Fallback", "styles": ["regular"]}
                ],
            },
            "sample",
        )

        self.assertEqual(result["family"], "Fallback")
        self.assertEqual(result["style"], "regular")
        self.assertEqual(result["weight"], 400)
        self.assertEqual(result["fullName"], "Fallback Regular")
        self.assertEqual(result["postScriptName"], "Unexpected-Exact-Name")

    def test_rejects_app_without_compatible_family(self):
        with self.assertRaisesRegex(FontConfigurationError, "no preferred font"):
            resolve_font(
                TYPOGRAPHY,
                "monospace",
                {
                    "mode": "configuration",
                    "availableFonts": [
                        {"family": "Unavailable", "styles": ["regular"]}
                    ],
                },
                "sample",
            )

    def test_rejects_invalid_required_postscript_name(self):
        typography = {
            "monospace": {
                "defaultStyle": "regular",
                "fonts": [
                    {
                        "family": "Broken",
                        "styles": {
                            "regular": {
                                "fullName": "Broken Regular",
                                "postScriptName": "Broken Name",
                            }
                        },
                    }
                ],
            }
        }
        with self.assertRaisesRegex(FontConfigurationError, "no preferred font"):
            resolve_font(
                typography,
                "monospace",
                {
                    "mode": "configuration",
                    "requiredProperties": ["postScriptName"],
                    "availableFonts": [
                        {"family": "Broken", "styles": ["regular"]}
                    ],
                },
                "sample",
            )


if __name__ == "__main__":
    unittest.main()
