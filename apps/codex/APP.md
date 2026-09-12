# Codex Adapter

Codex desktop reads its chrome colors and fonts from appearance tables in
`~/.codex/config.toml`. The generator replaces token references in
`config.template.toml`; the installer updates matching values in place without
reordering existing tables or keys.

The adapter selects the first configured UI and code font/style combination.
It prefers medium, falls back to regular, and uses the exact full and PostScript
names stored with that style.

- Distribution: Generated config snippet
- Operating systems: Windows, macOS
- Unsupported operating systems: Linux
- Global accessibility policy: 7.1:1 for required text pairs
- UI font preference when supported: Inter, then Noto Sans
- Monospace preference when supported: JetBrains Mono
- Codex CLI appearance remains controlled separately by its terminal host.
