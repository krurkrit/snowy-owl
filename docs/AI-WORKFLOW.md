# AI Workflow

## Minimize context

1. Read root `AGENTS.md` once.
1. Use its task-routing table to open only relevant files.
1. Search with `rg` before opening large files.
1. Ignore `generated/`, and `dist/` until generation or diff review.
1. Do not reload unchanged documentation during the same task.

## Make a change

1. State the scope: global token, dashboard, adapter, installer, or release.
1. Trace the affected token references and app mappings.
1. Edit source files or generators; never patch generated output.
1. Run the smallest useful check while iterating.
1. Regenerate only affected output, adapters, or documentation.
1. Review changed files for unrelated edits and unresolved token references.
1. Update `CHANGELOG.md` for user-visible behavior.
1. Run one final build once.

## Verification routing

| Change | Focused check | Final command |
| --- | --- | --- |
| Tokens or contrast | `python scripts/validate_contrast.py` | `./scripts/build.ps1 -All` |
| Typography, font manifest, or app fonts | `python scripts/validate_fonts.py` | `./scripts/build.ps1 -All` |
| Installer or OS support | `pwsh ./install.ps1 -Check` | `./scripts/build.ps1 -All` |
| HTML dashboard | `python scripts/validate_contrast.py --html` | `./scripts/build.ps1 -All -Html` |
| Generated adapters | `python scripts/generate.py` then `python scripts/check_generated.py` | `./scripts/build.ps1 -All` |
| Documentation | `./scripts/update-docs.ps1` | `./scripts/build.ps1 -All` |
| Documentation with dashboard | `./scripts/update-docs.ps1 -Html` | `./scripts/build.ps1 -All -Html` |

The final build already runs unit tests, contrast validation, token-document
generation, adapter generation, structural checks, preview generation, and VSIX
packaging. Do not run those same checks again afterward unless the build fails
and a fix changes the result.

## Completion checklist

- Source-of-truth files contain the intended change.
- Required contrast passes at 7.1:1 or higher without pre-rounding.
- References resolve without missing values or cycles.
- Every supported app font role resolves to an available family and face.
- Affected generated artifacts are current.
- Installers preserve settings outside Snowy Owl ownership.
- Unsupported capabilities are documented instead of patched.
- Changed Python modules and public APIs have useful `pydoc` docstrings.
- Tests and final build pass.
