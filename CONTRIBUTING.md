# Contributing

1. Create a feature branch from `main`.
2. Install dependencies with `python -m pip install .`.
3. Change source tokens, an app mapping, or another documented source file.
   Never hand-edit `generated/`, `dist/`, or generated documentation.
4. Follow the task routing and verification guidance in
   `docs/AI-WORKFLOW.md`.
   For a new app, also follow `docs/ADDING-APP.md`.
5. Update `CHANGELOG.md` for user-visible changes.
6. Run `./scripts/build.ps1 -All`; add `-Html` when the dashboard changed.
7. Open a PR. CI must pass before merge.
8. Releases are tags (`vX.Y.Z`) from `main`; no release branch is required.
