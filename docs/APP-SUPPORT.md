# App Support

| App | Windows | macOS | Linux | Font handling | Delivery |
| --- | --- | --- | --- | --- | --- |
| VS Code | Yes | Yes | Yes | User setting; warns if unavailable | VSIX |
| Warp | Yes | Yes | Yes | User setting; warns if unavailable | YAML |
| Slack | Yes | Yes | Yes | Not controlled | Guided setup |
| Codex desktop | Yes | Yes | No | Selects installed UI/code fonts | TOML config |
| Windows Terminal | Yes | No | No | Selects installed monospace font | JSON settings patch |
| PowerShell | Yes | Yes | Yes | Controlled by terminal host | Profile block |
| Obsidian | Yes | Yes | Yes | CSS fallback stacks; warns if unavailable | CSS snippet |

`APPS.yaml` is the machine-readable source for supported and unsupported OS
lists. “Yes” means the Snowy Owl adapter and its official app integration are
supported, not that every historical OS release remains supported by the app.
