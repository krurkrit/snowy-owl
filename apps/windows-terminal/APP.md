# Windows Terminal Adapter

Official settings.json supports custom color schemes, light/dark selection, and
profile font face. Installer patches only Snowy Owl-owned entries and backs up
settings.

The adapter selects the first supported monospace font/style and writes its
family and weight to profile defaults. Windows Terminal controls no separate UI
font.

- Distribution: JSON/settings patch
- Operating systems: Windows
- Unsupported operating systems: macOS, Linux
- Global accessibility policy: 7.1:1 for required text pairs
- UI font preference when supported: Inter, then Noto Sans
- Monospace preference when supported: JetBrains Mono
