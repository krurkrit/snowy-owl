import unittest
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from scripts.validate_contrast import (
    analyze_token_overrides,
    analyze_document_usage,
    build_html_report,
    build_variable_cards,
    find_app_token_reference_sources,
    find_app_token_references,
    format_token_error,
    get_variable_status,
    include_app_only_variables,
    merge_usage_details,
)
from scripts.generate_token_docs import build_report, flatten_tokens
from scripts.token_resolver import TokenConflictError


class ContrastTests(unittest.TestCase):
    def test_formats_token_conflict_without_traceback(self):
        root = Path("C:/project")
        message = format_token_error(
            TokenConflictError(
                "colors",
                "dark.background",
                1,
                [root / "tokens/colors.yaml", root / "apps/codex/colors.yaml"],
            ),
            root,
        )

        self.assertIn("ERROR: Token override conflict", message)
        self.assertIn("Variable: colors.dark.background", message)
        self.assertIn("Hierarchy: 1", message)
        self.assertIn("tokens\\colors.yaml", message)
        self.assertIn("increase snowyOwl.hierarchy", message)
        self.assertNotIn("Traceback", message)

    def test_debug_report_displays_unvalidated_warning(self):
        report = build_html_report([], 7.1, validation_skipped=True)

        self.assertIn("Validation skipped", report)
        self.assertIn("visual debugging only", report)

    def test_html_report_renders_foreground_on_background(self):
        report = build_html_report(
            [("sample-pair", "#123456", "#FEDCBA", 7.12345, True)],
            7.1,
            {
                "colors": {
                    "light": {
                        "background": "#FEDCBA",
                        "foreground": "#123456",
                        "unused": "{colors.base.unused}",
                    },
                    "dark": {"background": "#102030", "foreground": "#FAFAFA"},
                    "base": {"unused": "#123456"},
                },
                "typography": {
                    "ui": {
                        "defaultStyle": "regular",
                        "fonts": [
                            {
                                "family": "Example UI",
                                "styles": {"regular": {"weight": 400}},
                            },
                            {
                                "family": "sans-serif",
                                "styles": {"regular": {"weight": 400}},
                            },
                        ]
                    },
                    "monospace": {
                        "defaultStyle": "regular",
                        "fonts": [
                            {
                                "family": "Example Mono",
                                "styles": {"regular": {"weight": 400}},
                            },
                            {
                                "family": "monospace",
                                "styles": {"regular": {"weight": 400}},
                            },
                        ]
                    },
                },
            },
            {
                "colors": {
                    "colors.light.background": {
                        "apps": {"sample/mapping.yaml"},
                        "direct_apps": {"sample/mapping.yaml"},
                        "variables": set(),
                    },
                    "colors.base.unused": {
                        "apps": set(),
                        "direct_apps": set(),
                        "variables": {"colors.light.unused"},
                    },
                    "colors.light.foreground": {
                        "apps": {"sample/mapping.yaml"},
                        "direct_apps": set(),
                        "variables": set(),
                    },
                    "colors.light.unused": {
                        "apps": set(),
                        "direct_apps": set(),
                        "variables": set(),
                        "reference": "colors.base.unused",
                    },
                },
            },
            [
                {
                    "namespace": "contrast-rules",
                    "name": "Contrast",
                    "type": "contrast-rules",
                },
                {"namespace": "colors", "name": "Colors", "type": "color"},
                {
                    "namespace": "typography",
                    "name": "Typography",
                    "type": "typography",
                },
            ],
        )

        self.assertIn('style="color: #123456; background: #FEDCBA"', report)
        self.assertIn("sample-pair", report)
        self.assertIn("7.1235:1", report)
        self.assertIn("PASS", report)
        self.assertIn("colors.light.background", report)
        self.assertIn("colors.light.foreground", report)
        self.assertIn('href="#contrast"', report)
        self.assertIn('href="#colors"', report)
        self.assertIn('href="#typography"', report)
        self.assertIn("colors.base.unused", report)
        self.assertIn("colors.light.unused", report)
        self.assertIn("sample/mapping.yaml", report)
        self.assertIn('<span class="status used">Used</span>', report)
        self.assertIn(
            '<span class="status referenced">Referenced</span>', report
        )
        self.assertIn('<ul class="usage-list"></ul>', report)
        self.assertIn(
            '<li><a href="#token-colors-light-unused">'
            "colors.light.unused</a></li>",
            report,
        )
        self.assertIn(
            'class="color-reference" href="#token-colors-base-unused"', report
        )
        self.assertIn(
            'aria-label="Value from colors.base.unused"', report
        )
        self.assertIn(
            '<span class="value-tooltip" role="tooltip">'
            'Value from colors.base.unused</span>',
            report,
        )
        self.assertNotIn('title="Value from ', report)
        self.assertIn("Snowy Owl Token Usage and Accessibility", report)
        self.assertIn("Use dark background", report)
        self.assertIn('class="theme-icon icon-moon"', report)
        self.assertIn('class="theme-icon icon-sun"', report)
        self.assertIn('class="wcag-popover"', report)
        self.assertNotIn('<details class="wcag-popover"', report)
        self.assertIn(".wcag-popover:hover .wcag-tooltip", report)
        self.assertIn(".wcag-popover.popover-open .wcag-tooltip", report)
        self.assertIn("AA normal text", report)
        self.assertIn("AAA normal text", report)
        self.assertIn("4.5:1", report)
        self.assertIn("7:1", report)
        self.assertIn("grid-template-columns: repeat(2, minmax(0, 1fr))", report)
        self.assertIn("grid-template-columns: 7.25rem 1fr", report)
        self.assertIn('class="color-value"', report)
        self.assertIn(
            'class="usage-row variable-usage"><strong>Variables</strong>', report
        )
        self.assertIn('class="usage-row app-usage"><strong>Apps</strong>', report)
        self.assertIn(">owl</div>", report)
        self.assertIn("<strong>Variables</strong>", report)
        self.assertIn("<strong>Apps</strong>", report)
        self.assertIn("--page-background: #FEDCBA", report)
        self.assertIn("--page-background: #102030", report)
        self.assertIn("Typography", report)
        self.assertIn("Primary: Example UI", report)
        self.assertIn("Primary: Example Mono", report)
        self.assertIn("font-size: .875rem", report)
        self.assertIn("overflow-y: auto", report)
        self.assertIn(
            "dt { color: var(--text-secondary); font-size: .75rem; "
            "font-weight: 400",
            report,
        )
        self.assertIn("border-radius: .5rem", report)
        self.assertIn("--card-shadow: hsla(220, 30%, 5%, .07)", report)
        self.assertIn('class="sidebar-header"', report)
        self.assertIn('class="owl-logo"', report)
        self.assertIn('<span class="sidebar-title">Dashboard</span>', report)
        self.assertNotIn("Snowy Owl</strong><small>Design tokens", report)
        self.assertIn("font-weight: 500", report)
        self.assertIn(".variable-usage .usage-list { height: 3.75rem; }", report)
        self.assertIn(".app-usage .usage-list { height: 7.25rem; }", report)
        self.assertIn(".tokens { display: grid", report)
        self.assertIn("gap: 1rem; align-items: start; }", report)
        self.assertIn('id="token-colors-light-background"', report)
        self.assertNotIn('class="token-link"', report)
        self.assertIn('id="token-colors-light-foreground"', report)
        self.assertIn(
            '<li class="direct-use"><span class="app-name">'
            'sample/mapping.yaml</span><span class="usage-kind">Direct</span></li>',
            report,
        )
        self.assertIn(
            '<li class="indirect-use"><span class="app-name">'
            'sample/mapping.yaml</span><span class="usage-kind">Indirect</span></li>',
            report,
        )
        self.assertIn(".direct-use .usage-kind", report)
        self.assertIn(".token:hover { background: var(--action-hover); }", report)
        self.assertIn('<strong>6</strong> variables', report)
        self.assertIn('<strong>2</strong> used', report)
        self.assertIn('<strong>1</strong> referenced', report)
        self.assertIn('<strong>0</strong> historical', report)
        self.assertIn('<strong>3</strong> unused', report)
        self.assertIn('class="status-popover"', report)
        self.assertNotIn('<details class="status-popover"', report)
        self.assertIn(".status-popover:hover .status-tooltip", report)
        self.assertIn(".status-popover.popover-open .status-tooltip", report)
        self.assertIn(
            "<strong>3</strong> unused</span>\n"
            '          <div class="status-popover"',
            report,
        )
        self.assertIn(
            '<span class="status used">Used</span><span>Reaches an app.</span>',
            report,
        )
        self.assertIn(
            '<span class="status referenced">Referenced</span><span>Used by other active variables.</span>',
            report,
        )
        self.assertIn(
            '<span class="status historical">Historical</span>',
            report,
        )
        self.assertIn(".status-definition { display: grid", report)
        self.assertIn("gap: .75rem; align-items: start;", report)
        self.assertIn(".app-overridden-color .override-tooltip { display: none; }", report)
        self.assertIn(".app-floating-tooltip { position: fixed; z-index: 100;", report)
        self.assertIn('document.querySelectorAll(\".app-overridden-color\")', report)
        self.assertIn("rect.right - appTooltip.offsetWidth", report)
        self.assertIn("addDelayedPopover(\".status-popover, .wcag-popover\")", report)
        self.assertIn("setTimeout(() => popover.classList.remove(\"popover-open\"), 1000)", report)

    def test_color_cards_show_global_and_app_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            token_directory = root / "tokens"
            app_directory = root / "apps" / "sample"
            token_directory.mkdir(parents=True)
            app_directory.mkdir(parents=True)
            (token_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 0\n"
                "base: '#FFFFFF'\nlight:\n  background: '{colors.base}'\n",
                encoding="utf-8",
            )
            (token_directory / "colors.override.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 1\n"
                "light:\n  background: '#FDFDFD'\n",
                encoding="utf-8",
            )
            (token_directory / "colors.override2.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 2\n"
                "light:\n  background: '#FBFBFB'\n",
                encoding="utf-8",
            )
            (app_directory / "colors.override.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 3\n"
                "light:\n  background: '#FAFAFA'\n",
                encoding="utf-8",
            )
            (app_directory / "colors.yaml").write_text(
                "snowyOwl:\n  name: Colors\n  type: color\n  hierarchy: 2\n"
                "light:\n  background: '#FCFCFC'\n  custom: '#ABCDEF'\n",
                encoding="utf-8",
            )

            overrides = analyze_token_overrides(token_directory, root / "apps")
            details = overrides["colors"]["colors.light.background"]
            self.assertEqual(
                details["global_override"],
                {
                    "history": [
                        {
                            "value": "#FFFFFF",
                            "source": "colors.yaml",
                            "active": False,
                            "reference": "colors.base",
                            "overridden_by": "colors.override.yaml",
                        },
                        {
                            "value": "#FDFDFD",
                            "source": "colors.override.yaml",
                            "active": False,
                            "overridden_by": "colors.override2.yaml",
                        },
                        {
                            "value": "#FBFBFB",
                            "source": "colors.override2.yaml",
                            "active": True,
                        },
                    ]
                },
            )
            self.assertEqual(
                details["app_overrides"],
                {
                    "sample/colors.yaml": {
                        "value": "#FCFCFC",
                        "active": False,
                        "overridden_by": "sample/colors.override.yaml",
                    },
                    "sample/colors.override.yaml": {
                        "value": "#FAFAFA",
                        "active": True,
                    },
                },
            )
            app_only = overrides["colors"]["colors.light.custom"]
            self.assertTrue(app_only["app_only"])
            self.assertEqual(
                app_only["app_overrides"]["sample/colors.yaml"],
                {"value": "#ABCDEF", "active": True},
            )
            report_tokens = include_app_only_variables(
                {"colors": {"light": {"background": "#FBFBFB"}}},
                overrides,
            )
            self.assertEqual(
                report_tokens["colors"]["light"]["custom"], "#ABCDEF"
            )
            usage = merge_usage_details(
                {},
                overrides,
                {"colors.light.custom": {"sample/mapping.yaml"}},
            )
            self.assertEqual(
                get_variable_status(usage["colors"]["colors.light.custom"]),
                "used",
            )

            cards = "\n".join(
                build_variable_cards(
                    "colors",
                    {"light": {"background": "#FBFBFB"}},
                    {"colors.light.background": details},
                )
            )
            self.assertIn('class="color-value original-value">#FFFFFF</code>', cards)
            self.assertIn(
                'class="color-reference" href="#token-colors-base" '
                'aria-label="Value from colors.base. Overridden by '
                'colors.override.yaml"><code '
                'class="color-value original-value">#FFFFFF</code></a>',
                cards,
            )
            self.assertIn(
                "Value from colors.base<br>Overridden by colors.override.yaml",
                cards,
            )
            self.assertNotIn(
                'aria-label="Value from colors.base<br>', cards
            )
            self.assertNotIn(
                '<li class="historical-use"><a href="#token-colors-base">'
                'colors.base</a><span class="usage-kind">'
                'Historical</span></li>',
                cards,
            )
            self.assertIn('class="color-value original-value">#FDFDFD</code>', cards)
            self.assertIn('class="color-value override-value">#FBFBFB</code>', cards)
            self.assertIn("Overridden by colors.override.yaml", cards)
            self.assertIn("Overridden by colors.override2.yaml", cards)
            self.assertIn('class="app-override-value superseded">#FCFCFC', cards)
            self.assertIn('class="overridden-color app-overridden-color"', cards)
            self.assertIn("sample/colors.override.yaml", cards)
            self.assertIn(
                "Overridden by sample/colors.override.yaml", cards
            )
            self.assertIn(
                'class="app-override-value active-override">#FAFAFA', cards
            )
            self.assertNotIn('<span class="usage-kind">Override</span>', cards)

            usage = analyze_document_usage(
                {
                    "colors": {
                        "base": "#FFFFFF",
                        "light": {"background": "#FBFBFB"},
                    }
                },
                {},
            )
            merge_usage_details(usage, overrides)
            self.assertEqual(
                get_variable_status(usage["colors"]["colors.base"]),
                "historical",
            )
            self.assertEqual(
                usage["colors"]["colors.base"]["superseded_variables"],
                {"colors.light.background"},
            )
            reverse_cards = "\n".join(
                build_variable_cards(
                    "colors",
                    {"base": "#FFFFFF"},
                    {"colors.base": usage["colors"]["colors.base"]},
                )
            )
            self.assertIn(
                '<li class="historical-use"><a '
                'href="#token-colors-light-background">'
                'colors.light.background</a><span '
                'class="usage-kind">Historical</span></li>',
                reverse_cards,
            )

    def test_finds_variables_not_referenced_by_apps(self):
        documents = {
            "colors": {
                "base": {"used": "#FFFFFF", "unused": "#000000"},
                "background": "{colors.base.used}",
                "unused": "{colors.base.unused}",
            }
        }
        usage = analyze_document_usage(
            documents, {"colors.background": {"sample/mapping.yaml"}}
        )

        self.assertTrue(usage["colors"]["colors.base.used"]["apps"])
        self.assertFalse(usage["colors"]["colors.base.unused"]["apps"])

    def test_app_group_reference_uses_all_descendants(self):
        documents = {
            "colors": {
                "base": {"one": "#FFFFFF", "two": "#000000"},
                "light": {
                "foreground": "{colors.base.one}",
                "background": "{colors.base.two}",
                },
            }
        }
        usage = analyze_document_usage(
            documents, {"colors.light": {"sample/mapping.yaml"}}
        )

        self.assertTrue(usage["colors"]["colors.base.one"]["apps"])
        self.assertTrue(usage["colors"]["colors.base.two"]["apps"])

    def test_finds_references_in_app_source_files(self):
        with tempfile.TemporaryDirectory() as directory:
            app_directory = Path(directory)
            (app_directory / "mapping.yaml").write_text(
                'theme: "{colors.light}"\n', encoding="utf-8"
            )
            (app_directory / "config.toml").write_text(
                'accent = "{colors.orange.accent}"\n', encoding="utf-8"
            )

            self.assertEqual(
                find_app_token_references(app_directory),
                {"colors.light", "colors.orange.accent"},
            )
            self.assertEqual(
                find_app_token_reference_sources(app_directory),
                {
                    "colors.light": {"mapping.yaml"},
                    "colors.orange.accent": {"config.toml"},
                },
            )

    def test_usage_lists_apps_and_token_dependents(self):
        documents = {
            "colors": {
                "base": {"source": "#FFFFFF", "alias": "{colors.base.source}"},
                "surface": "{colors.base.alias}",
            }
        }
        usage = analyze_document_usage(
            documents, {"colors.surface": {"sample/mapping.yaml"}}
        )

        self.assertEqual(
            usage["colors"]["colors.base.source"]["variables"],
            {"colors.base.alias"},
        )
        self.assertEqual(
            usage["colors"]["colors.base.alias"]["variables"],
            {"colors.surface"},
        )
        self.assertEqual(
            usage["colors"]["colors.base.alias"]["reference"],
            "colors.base.source",
        )
        self.assertEqual(
            usage["colors"]["colors.base.source"]["apps"],
            {"sample/mapping.yaml"},
        )

    def test_variable_usage_statuses(self):
        self.assertEqual(get_variable_status({"apps": {"app/mapping.yaml"}}), "used")
        self.assertEqual(
            get_variable_status({"apps": set(), "variables": {"colors.light"}}),
            "referenced",
        )
        self.assertEqual(
            get_variable_status(
                {"superseded_variables": {"colors.dark.background"}}
            ),
            "historical",
        )
        self.assertEqual(get_variable_status({}), "unused")
        self.assertEqual(
            get_variable_status(
                {"app_overrides": {"sample/colors.yaml": {"active": True}}}
            ),
            "unused",
        )

    def test_token_report_lists_nested_colors(self):
        tokens = {
            "colors": {"light": {"background": "#FFFFFF"}},
        }

        self.assertEqual(
            list(flatten_tokens(tokens["colors"])), [("light.background", "#FFFFFF")]
        )
        report = build_report(tokens)
        self.assertIn("`colors.light.background` | `#FFFFFF`", report)


if __name__ == "__main__":
    unittest.main()
