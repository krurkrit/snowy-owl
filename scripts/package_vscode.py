#!/usr/bin/env python3
"""Package the generated Snowy Owl VS Code extension as a VSIX archive."""

from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

R = Path(__file__).resolve().parents[1]
app = R / "apps/vscode"
dist = R / "dist"
dist.mkdir(exist_ok=True)
pkg = json.loads((app / "package.json").read_text(encoding="utf-8"))
v = pkg["version"]
publisher = pkg["publisher"]
out = dist / f"snowy-owl-{v}.vsix"
manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">
  <Metadata>
    <Identity Language="en-US" Id="snowy-owl" Version="{v}" Publisher="{publisher}" />
    <DisplayName>Snowy Owl</DisplayName>
    <Description xml:space="preserve">Snowy Owl accessible light and dark color themes.</Description>
    <Tags>theme,color-theme,snowy-owl</Tags>
    <Categories>Other</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.90.0" />
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="ui,workspace" />
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code" Version="[1.90.0,)" />
  </Installation>
  <Dependencies />
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true" />
  </Assets>
</PackageManifest>"""
content = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="application/json" />
  <Default Extension="md" ContentType="text/markdown" />
  <Default Extension="vsixmanifest" ContentType="text/xml" />
</Types>"""
with ZipFile(out, "w", ZIP_DEFLATED) as z:
    z.writestr("extension.vsixmanifest", manifest)
    z.writestr("[Content_Types].xml", content)
    for f in [
        app / "package.json",
        app / "README.md",
        *sorted((app / "themes").glob("*.json")),
    ]:
        z.write(f, "extension/" + str(f.relative_to(app)).replace("\\", "/"))
print(out)
