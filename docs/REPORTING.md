# Token Dashboard

`scripts/validate_contrast.py --html` generates `docs/index.html`. Do not edit
the HTML directly.

For visual debugging while token or app overrides are temporarily invalid, run
`./scripts/update-docs.ps1 -Html -SkipValidation`. The generated page displays
an unvalidated warning and does not rewrite the accessibility report. Global
YAML must still be parseable and references must still resolve because the
renderer needs concrete token values.

## Inputs

- `tokens/*.yaml`: section metadata and token values
- `apps/<app>/**/*.{yaml,yml}` with `snowyOwl`: app-specific override layers
- `tokens/contrast-rules.yaml`: required foreground/background pairs
- Supported text configuration files under `apps/`: token-reference usage
- `scripts/validate_contrast.py`: analysis and rendering behavior

Each token document declares `snowyOwl.name`, `snowyOwl.type`, and optional
`snowyOwl.hierarchy` (default `0`). Files sharing a filename prefix merge into
one namespace. Higher hierarchy values override lower values. A type selects
its renderer; a name must never select behavior.

Global and app hierarchies are separate scopes. Duplicate conflicting values
fail within one scope, while a resolved app scope always overlays the resolved
global scope.

## Color usage

- **Used:** the token reaches at least one app, directly or through another token.
- **Referenced:** another active token references it, but no app reaches it.
- **Historical:** only a currently overridden token value references it, so it
  has no effect on generated apps.
- **Unused:** neither another token nor an app references it.
- **Direct:** the app file contains that exact token reference.
- **Indirect:** the app reaches the token through another token reference.

A global override lists its complete value history. Each superseded code is
struck through and identifies the next overriding file on hover or focus; the
path is relative to `tokens/` and the effective code remains plain. App-local
history appears in the Apps area, where
superseded codes are struck through and the effective code receives a blue
rounded outline.

When a superseded value is a token reference, its struck-through color code
links to that referenced token card. The referenced token's Variables area
lists the historical source with a **Historical** badge.

The Variables area is an inbound dependency list: it shows every variable that
uses the card's value, including superseded references that would become active
again if an override were removed. Outbound references remain available through
linked color codes. Empty usage lists render blank. Long lists scroll inside the
card.

When a color value references another token, its displayed color code links to
that source token and shows a styled tooltip on hover or focus. Superseded
referenced values combine the reference and overriding-file information in one
tooltip, displayed on separate lines. App override history stays in the Apps
area; struck-through app values show the next overriding filename on hover or
focus. App-level tooltips render in a fixed page layer aligned to the end of
the color code, so scrollable Apps lists and the viewport cannot clip them.

App-only color variables receive report cards marked **App-only**. Their
effective values remain scoped to the declaring app and do not enter the global
token set.

## UI rules

- Follow the MUI dashboard's typography, spacing, navigation, card, chip, and
  interaction patterns.
- Render status definitions with the same colored rounded chips as color cards.
- Keep the WCAG and color-status popovers open while their content is hovered;
  close them one second after the pointer leaves the trigger or content.
- Use token-derived light and dark colors; do not duplicate the palette in HTML.
- Preserve keyboard focus, meaningful labels, and reduced-motion compatibility.
- Keep sections and navigation metadata-driven.

## Verification

During development, run `python scripts/validate_contrast.py --html`. When the
change is ready, run `./scripts/build.ps1 -All -Html` once.
