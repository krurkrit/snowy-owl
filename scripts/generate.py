#!/usr/bin/env python3
"""Generate native app artifacts from global and app-layer personalization."""

from pathlib import Path
import json
import re
import shutil

from font_resolver import resolve_app_fonts
from token_resolver import load_token_documents, load_yaml, resolve_references

R = Path(__file__).resolve().parents[1]
tokens = load_token_documents(R / "tokens")
app_registry = load_yaml(R / "APPS.yaml")["apps"]
app_mappings = {}
app_tokens = {}
for mapping_path in sorted((R / "apps").glob("*/mapping.yaml")):
    mapping = load_yaml(mapping_path)
    app = mapping_path.parent.name
    app_tokens[app] = load_token_documents(R / "tokens", [mapping_path.parent])
    resolve_references(mapping, app_tokens[app])
    app_mappings[app] = mapping

font_selections = {
    app: resolve_app_fonts(app_tokens[app]["typography"], mapping, app)
    for app, mapping in app_mappings.items()
}
(R / "generated").mkdir(parents=True, exist_ok=True)
(R / "generated/font-selections.json").write_text(
    json.dumps(font_selections, indent=2) + "\n", encoding="utf-8"
)
(R / "generated/apps.json").write_text(
    json.dumps(app_registry, indent=2) + "\n", encoding="utf-8"
)

apps = ["vscode", "warp", "windows-terminal", "powershell", "obsidian", "codex"]
for sub in apps:
    out = R / "generated" / sub
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
if (R / "apps/vscode/themes").exists():
    shutil.copytree(R / "apps/vscode/themes", R / "generated/vscode/themes")
for f in (R / "apps/warp").glob("snowy-owl-*.yaml"):
    shutil.copy2(f, R / "generated/warp" / f.name)
for app, patterns in {
    "windows-terminal": ["*.json"],
    "powershell": ["snowy-owl.ps1"],
    "obsidian": ["snowy-owl.css"],
}.items():
    for pat in patterns:
        for f in (R / "apps" / app).glob(pat):
            shutil.copy2(f, R / "generated" / app / f.name)

codex_mapping = load_yaml(R / "apps/codex/mapping.yaml")
codex_template = (R / "apps/codex" / codex_mapping["template"]).read_text(
    encoding="utf-8"
)
token_placeholder = re.compile(r"\{[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\}")


def replace_token(match):
    """Resolve one Codex template placeholder to a scalar app token value."""
    documents = {**app_tokens["codex"], "font": font_selections["codex"]}
    value = resolve_references(match.group(0), documents)
    if not isinstance(value, (str, int, float, bool)):
        raise TypeError(f"Template token must be scalar: {match.group(0)}")
    return str(value)


desktop_theme = token_placeholder.sub(replace_token, codex_template)
(R / "generated/codex/snowy-owl-desktop.toml").write_text(
    desktop_theme, encoding="utf-8"
)

terminal_path = R / "generated/windows-terminal/snowy-owl-schemes.json"
terminal_config = json.loads(terminal_path.read_text(encoding="utf-8"))
terminal_font = font_selections["windows-terminal"]["monospace"]
terminal_config["profileDefaults"]["font"] = {
    "face": terminal_font["family"],
    "weight": terminal_font["weight"],
}
terminal_path.write_text(
    json.dumps(terminal_config, indent=2) + "\n", encoding="utf-8"
)
print("Generated Snowy Owl outputs for all native adapters.")
