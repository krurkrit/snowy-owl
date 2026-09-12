#!/usr/bin/env python3
"""Validate and display font selection for every app adapter."""

from pathlib import Path

from font_resolver import resolve_app_fonts
from token_resolver import load_token_documents, load_yaml


ROOT = Path(__file__).resolve().parents[1]


def main():
    """Validate and print font selections for every app-specific token layer."""
    for path in sorted((ROOT / "apps").glob("*/mapping.yaml")):
        app = path.parent.name
        typography = load_token_documents(
            ROOT / "tokens", [path.parent]
        )["typography"]
        fonts = resolve_app_fonts(typography, load_yaml(path), app)
        summary = []
        for role, selection in fonts.items():
            if selection["mode"] == "unsupported":
                summary.append(f"{role}=unsupported")
            else:
                summary.append(
                    f"{role}={selection['family']} {selection['style']} "
                    f"({selection['mode']})"
                )
        print(f"FONT {app}: {', '.join(summary)}")


if __name__ == "__main__":
    main()
