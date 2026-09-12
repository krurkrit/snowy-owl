#!/usr/bin/env python3
"""Set Snowy Owl version in all package metadata."""

from pathlib import Path
import json
import re
import sys

R = Path(__file__).resolve().parents[1]
if len(sys.argv) != 2 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
    raise SystemExit("usage: python3 scripts/set_version.py X.Y.Z")
v = sys.argv[1]
(R / "VERSION").write_text(v + "\n", encoding="utf-8", newline="\n")
p = R / "apps/vscode/package.json"
data = json.loads(p.read_text(encoding="utf-8"))
data["version"] = v
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
pyproject = R / "pyproject.toml"
pyproject_text = pyproject.read_text(encoding="utf-8")
pyproject_text, count = re.subn(
    r'(?m)^version = "\d+\.\d+\.\d+"$',
    f'version = "{v}"',
    pyproject_text,
    count=1,
)
if count != 1:
    raise SystemExit("pyproject.toml must contain exactly one project version")
pyproject.write_text(pyproject_text, encoding="utf-8", newline="\n")
print(v)
