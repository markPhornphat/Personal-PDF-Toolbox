# Developer release guide

## Build locally

Use Windows x64 with uv and Python 3.12. Run these PowerShell commands from the repository root.

```powershell
uv sync --locked
$env:QT_QPA_PLATFORM = 'offscreen'
uv run --locked ruff check src tests scripts
uv run --locked mypy --ignore-missing-imports src
uv run --locked pytest
./scripts/install-compiler.ps1
./scripts/build.ps1
./scripts/smoke-install.ps1
```

The build places `PDF-Toolbox-Setup-x64.exe` and `SHA256SUMS.txt` in `dist`. The Inno Setup compiler download is pinned to its SHA-256. Use `-Compiler` to point to an existing pinned compiler. For publisher signing, Authenticode-sign the completed installer before generating or signing its release manifest. Regenerate the checksum and repeat the installer smoke test after signing. Windows may show SmartScreen prompts for unsigned installers.

## GitHub workflow

Update `project.version` in `pyproject.toml` and add matching release notes to `CHANGELOG.md`. Run the tests and commit the change. With repository-owner authorization, push the branch. Main runs the Windows tests and packages an installer artifact. Manual builds are available under **Actions → Windows release → Run workflow**.

Configure the release environment and variables in [Updater setup](UPDATER_SETUP.md). Once publication is enabled, successful main builds can publish a version newer than the latest stable release. The publish job verifies the build checksum, signs the manifest and uploads all assets to a draft before publishing it. Existing release installers are immutable under the workflow. Keep the protected environment restricted to main.

If packaging fails, inspect the corresponding build or installation log and replay the step locally. If GitHub draft upload or finalization fails, inspect the draft and its assets before retrying. An authorized maintainer can remove a failed draft using GitHub, then run the workflow again. Keep the last verified installer for manual recovery if an upgrade fails.
