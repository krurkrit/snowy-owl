# Adding an App

Use the app's current, official personalization mechanism. Do not patch binaries
or unsupported internal files.

1. Add the app to `APPS.yaml`.
   List the supported Windows, macOS, and Linux platforms in
   `supportedOperatingSystems`; omitted platforms are unsupported.
1. Create `apps/<name>/APP.md` with supported capabilities, limitations, and the
   official integration surface.
1. Create `apps/<name>/AGENTS.md` containing only app-specific constraints.
1. Map role-based `{colors.*}` tokens in `apps/<name>/mapping.yaml`; avoid raw
   values when a suitable color role exists.
1. Optionally add `apps/<name>/<namespace>.override.yaml` with `snowyOwl`
   metadata and a higher hierarchy to override tokens for only that app.
1. Add the native source or template consumed by the generator.
1. Add idempotent installation that preserves unrelated settings and backs up
   user-owned configuration before changing it. Add uninstall behavior only
   when owned changes can be removed safely.
1. Check required fonts before personalization. Select an installed fallback or
   warn; never silently download or execute third-party font installers.
1. Include the app in generation, validation, packaging, tests, and user-facing
   documentation.
1. Run `./scripts/build.ps1 -All` before opening a pull request.

Declare unsupported capabilities explicitly instead of approximating them with
unsupported customization.
