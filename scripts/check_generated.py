#!/usr/bin/env python3
"""Check generated app artifacts for required structure and resolved tokens."""

from pathlib import Path
import json
import re

from token_resolver import load_yaml

R = Path(__file__).resolve().parents[1]
platforms = {"windows", "macos", "linux"}
registry = load_yaml(R / "APPS.yaml")["apps"]
for app, config in registry.items():
    supported = set(config.get("supportedOperatingSystems", []))
    if not supported or not supported <= platforms:
        raise SystemExit(
            f"{app}: supportedOperatingSystems must be a non-empty subset of {platforms}"
        )
font_manifest = R / "generated/font-selections.json"
if not font_manifest.is_file():
    raise SystemExit("Expected generated font selection manifest")
font_data = json.loads(font_manifest.read_text(encoding="utf-8"))
if set(font_data) != set(registry):
    raise SystemExit("Font manifest and app registry do not contain the same apps")
generated_registry = json.loads((R / "generated/apps.json").read_text(encoding="utf-8"))
if generated_registry != registry:
    raise SystemExit("Generated app registry is stale")
files = list((R / "generated/vscode/themes").glob("*.json"))
if len(files) != 2:
    raise SystemExit("Expected two generated VS Code themes")
for f in files:
    json.loads(f.read_text(encoding="utf-8"))
warp = list((R / "generated/warp").glob("*.yaml"))
if len(warp) != 2:
    raise SystemExit("Expected two generated Warp themes")
codex = R / "generated/codex/snowy-owl-desktop.toml"
if not codex.is_file():
    raise SystemExit("Expected generated Codex desktop theme")
codex_text = codex.read_text(encoding="utf-8")
if re.search(r"\{(?:colors|typography|font)\.", codex_text):
    raise SystemExit("Generated Codex theme contains unresolved token references")
for section in (
    "[desktop.appearanceLightChromeTheme]",
    "[desktop.appearanceDarkChromeTheme]",
):
    if section not in codex_text:
        raise SystemExit(f"Missing generated Codex section: {section}")
installers = sorted((R / "apps").glob("*/install.ps1"))
app_directories = sorted(path for path in (R / "apps").iterdir() if path.is_dir())
if len(installers) != len(app_directories):
    raise SystemExit("Every app directory must contain install.ps1")
print("Generated outputs look structurally valid.")
