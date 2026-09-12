# Agent Instructions

## Goal

Maintain one accessible token system across every supported app. Prefer small,
traceable changes and keep generated output reproducible.

## Read only what the task needs

| Task | Read next |
| --- | --- |
| Global colors or fonts | `docs/DESIGN-SYSTEM.md`, `docs/ARCHITECTURE.md` |
| HTML dashboard/report | `docs/REPORTING.md`, `scripts/validate_contrast.py` |
| Existing app | `apps/<app>/AGENTS.md`, `APP.md`, `mapping.yaml` |
| New app | `docs/ADDING-APP.md` |
| Release | `docs/RELEASE.md` |

Use `docs/AI-WORKFLOW.md` for validation and completion rules. Do not read every
app directory for a change scoped to one app.

## Sources of truth

- `tokens/*.yaml`: global design tokens, report metadata, and contrast policy
- `fonts/manifest.json`: pinned optional font downloads, styles, and checksums
- `apps/<app>/**/*.{yaml,yml}` with `snowyOwl`: app-local token overrides
- `APPS.yaml`: supported-app registry
- `apps/<app>/mapping.yaml`: app-to-token mapping
- App-owned templates and native source files under `apps/<app>/`

`generated/`, `dist/`, `docs/TOKENS.md`, `docs/ACCESSIBILITY.md`,
`docs/images/snowy-owl-preview.png`, and `docs/index.html` are generated. Change
their inputs or generators, then regenerate them.

## Invariants

- Required contrast pairs must be at least 7.1:1; never round before pass/fail.
- Color roles reference other values through `{colors.*}`. Higher-hierarchy
  files may override lower-hierarchy values.
- Prefer Inter → Noto Sans → system UI and JetBrains Mono for monospace.
- Keep fonts and their styles in preference order. Store exact full and
  PostScript names; never derive them. Every app mapping must
  declare both font roles and mark unsupported roles explicitly.
- Use official app configuration APIs; never patch app binaries or unsupported
  internals.
- Keep installers idempotent and preserve unrelated user settings.
- Keep every adapter's Windows, macOS, and Linux support explicit in
  `APPS.yaml`. Check required fonts before applying personalization.
- Handle app limitations in that adapter; do not weaken global tokens for one app.
- Give Python modules and public APIs concise docstrings that render correctly
  with `python -m pydoc <module>`.

## Workflow

Understand scope → inspect inputs → edit source → run targeted checks → generate
affected output → review the diff → update user-facing docs/changelog → run one
final full build.

## Commands

- Final verification: `./scripts/build.ps1 -All`
- Final verification plus HTML report: `./scripts/build.ps1 -All -Html`
- Documentation only: `./scripts/update-docs.ps1 -Html`

Do not run the full build repeatedly while editing. Use focused checks first,
then run the appropriate full-build command once when the change is ready.
