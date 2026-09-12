# Snowy Owl Design System

Snowy Owl uses a paper-like `#F8F9FA` light surface and a near-black `#18191B`
dark surface. Blue is the primary interactive family; orange is the
secondary/accent family. Status colors are semantic and use explicit foreground
pairs.

`tokens/colors.yaml` defines primitive colors and interface roles in one
`colors` namespace. App mappings consume roles such as
`colors.light.foreground`, `colors.light.background`, and `colors.status`.

Typography uses ordered font and style preferences. UI starts with Inter and
falls back to Noto Sans, then the generic sans-serif family. Monospace starts
with JetBrains Mono and falls back to Cascadia Mono, Consolas, then the generic
monospace family. Each adapter selects only font/style combinations it supports.

See `ACCESSIBILITY.md` for generated contrast results.
