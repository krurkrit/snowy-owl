# Release

Snowy Owl uses trunk-based development: feature branches → PR → `main`. No
release branch is needed.

1. Update `VERSION` and `CHANGELOG.md`.
1. Merge to `main`; CI validates and builds downloadable workflow artifacts.
1. Tag the main commit `vX.Y.Z`.
1. The release workflow validates, builds, packages, calculates SHA-256
   checksums, and creates a GitHub Release.
1. VS Code Marketplace publishing is optional when `VSCE_PAT` and a real
   publisher are configured.
