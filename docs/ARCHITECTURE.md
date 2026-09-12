# Architecture

Snowy Owl is a portable personalization system. Global tokens describe the
design once; app adapters translate those tokens into supported native formats.

## Repository map

| Path | Purpose | Edit directly? |
| --- | --- | --- |
| `tokens/` | Global colors, typography, and contrast policy | Yes |
| `fonts/manifest.json` | Pinned optional font downloads and checksums | Yes |
| `APPS.yaml` | Supported-app capabilities and delivery registry | Yes |
| `apps/<app>/mapping.yaml` | References from an app to global tokens | Yes |
| `apps/<app>/APP.md` | Adapter contract and limitations | Yes |
| `apps/<app>/install.ps1` | Idempotent app installer | Yes |
| `scripts/` | Validation, generation, packaging, and documentation tools | Yes |
| `tests/` | Resolver and report behavior | Yes |
| `generated/` | Rebuilt native adapter artifacts | No |
| `dist/` | Packages and release artifacts | No |
| `docs/index.html` | Generated token dashboard | No |
| `docs/TOKENS.md` | Generated token reference | No |

App directories may contain native source templates or checked-in native files
that `scripts/generate.py` copies into `generated/`. Edit the app copy, never the
generated copy.

## Pipeline

Pipeline: tokens → resolve → WCAG validation (project floor 7.1:1) → app
generation → native validation/build → preview → package/release.

The root `install.ps1` discovers and dispatches to `apps/*/install.ps1`.
Cross-app installer helpers live in `scripts/install-common.ps1`; app-specific
installation logic stays with its adapter.

An app limitation must be handled in its adapter. Do not weaken or change global
tokens solely to satisfy one app. Prefer official configuration/theme
mechanisms; do not patch application binaries or unsupported internals.

## Token references

Token YAML files form namespaces from the part of the filename before the first
dot. Thus, `colors.yaml` and `colors.override.yaml` both contribute to the
`colors` namespace. A scalar containing
`{namespace.path.to.value}` references another token while preserving the
referenced value's type. For example, `{colors.light.background}` resolves from
`tokens/colors.yaml`.

References must occupy the complete scalar value. The resolver rejects missing
references and cycles before validation or generation. Primitive colors and
semantic roles share the `colors` namespace; contrast rules and app mappings
reference `{colors.*}` or typography tokens directly.

## Layered overrides

Every token document has a non-negative `snowyOwl.hierarchy`, defaulting to
`0`. Documents are deeply merged by namespace from the lowest hierarchy to the
highest. A higher value replaces conflicting lower values while retaining
unrelated properties. Conflicting values at the same hierarchy are invalid.

Global layers live in `tokens/`. App-specific layers may live anywhere under
`apps/<app>/` and affect only that adapter. Name them using the target namespace
as the filename prefix, for example `apps/codex/colors.override.yaml`.
Hierarchy is evaluated independently inside the global scope and inside each
app scope. After both scopes are resolved, the app result overlays the global
result regardless of whether their hierarchy numbers are equal.
An app scope may also append tokens that do not exist globally. Those tokens
remain available only while resolving and generating that app.

## Font negotiation

`tokens/typography.yaml` stores fonts in preference order and exact metadata for
each available style.
Every app mapping declares `fonts.ui` and `fonts.monospace` with one mode:
`configuration`, `runtime-stack`, `user-setting`, or `unsupported`. Configurable
roles also declare `availableFonts`, including the styles accepted for each
family. An app can override the role's `defaultStyle` with `style`.

`scripts/validate_fonts.py` selects the first preferred font with a compatible
style. A supported role with no match fails validation. Runtime stacks retain
every compatible family in fallback order; single-value configurations use the
first match.

Full font names and PostScript names are stored explicitly per style. Never
construct them from the family and style: they are font metadata and may not
follow a predictable naming pattern. Adapters declare `requiredProperties` when
their configuration needs those identifiers. Validation also enforces the
OpenType PostScript-name length and character restrictions.

`fonts/manifest.json` pins the optional Google Fonts downloads, their licenses,
and SHA-256 checksums. `scripts/install-fonts.ps1` verifies every download and
installs it for the current user on Windows, macOS, or Linux. Font installation
is always explicit; app installers otherwise keep their existing warning and
fallback behavior.

Generation writes `generated/font-selections.json`. Installers compare those
ordered candidates with locally installed fonts before changing configuration.
They select the first detected candidate or warn and leave fallback behavior to
the app or operating system. Font files are never downloaded silently.

## Operating systems

`APPS.yaml` partitions `windows`, `macos`, and `linux` into supported and
unsupported lists for every adapter. Generation writes this registry to
`generated/apps.json`, which installers use to skip unsupported adapters with a
clear message. PowerShell 7 is the portable installer runtime.

## Token document metadata

Every token file declares metadata in a top-level `snowyOwl`
property:

```yaml
---
snowyOwl:
  name: Override Colors
  type: color
  hierarchy: 1
light:
  background: "#FDFDFD"
```

The loader removes `snowyOwl` before merging and resolving references. Its name
labels the merged document, its type selects the renderer, and its hierarchy
controls precedence. Supported report types are `color`, `contrast-rules`, and
`typography`.

## Generated report

`scripts/validate_contrast.py --html` discovers token documents from their
`snowyOwl` metadata and writes `docs/index.html`. Report names and namespaces
must come from metadata rather than fixed filenames. See `docs/REPORTING.md`
for rendering and usage-status rules.
