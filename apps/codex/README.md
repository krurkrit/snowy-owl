# Codex

Run `install.ps1 -App codex` to apply the generated light and dark Snowy Owl
appearance values to `~/.codex/config.toml`. Existing sections and keys retain
their order, unrelated values are preserved, and the current file is backed up
as `config.toml.snowy-owl.bak`. Missing theme keys or tables are appended.
Restart Codex after installation.

These `desktop.appearance*ChromeTheme` tables are written by the Codex desktop
app but are not currently part of the published Codex configuration reference,
so their schema may change. Codex CLI appearance remains controlled separately
by its terminal host.
