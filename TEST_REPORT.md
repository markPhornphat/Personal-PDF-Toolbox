# PDF Toolbox 0.1.0 development report

PDF Toolbox provides five local Windows GUI workspaces for merge and append, split, remove and extract, conversion to JPG and PNG, and visual PDF editing. The Windows x64 installer is built from the same source. See the [feature matrix](FEATURE_MATRIX.md), [dashboard](docs/screenshots/dashboard.png), [merge workspace](docs/screenshots/merge.png) and [editor](docs/screenshots/editor.png).

## Verified locally

- Windows 11 x64 build 26300, CPython 3.12.16. The locked runtime uses PySide6 Essentials 6.10.2, pypdf 6.9.2, pypdfium2 5.15.2, Pillow 12.2.0, cryptography 47.0.0 and pywin32-ctypes 0.2.3.
- 18 pytest cases passed, including seven GUI cases rerun at 2× Qt scaling. Ruff and mypy passed. The lock resolved offline with the local dependencies. The Windows workflows passed actionlint.
- The offscreen Qt tests ran all five workspace export paths and inspected the resulting PDFs and images. They covered Unicode filenames, protected input, page order and duplication, range validation, transparent PNG, file drops, file-reference paste, screenshot paste, undo and source preservation.
- The editor preserved original page rotation and matched the expected crop-relative overlay placement for 0°, 90°, 180° and 270°. The bundled font produced visible Thai glyphs and vector text in the PDF fixture.
- The updater tests used an in-memory GitHub transport with a generated test key. Manifest tampering, wrong repository, altered installer, interrupted transfer, cancelled download, draft releases and disallowed redirects were exercised. The local Windows trust helper accepted the signed Inno Setup compiler.
- PyInstaller and Inno Setup built the Windows bundle and installer. The packaged startup smoke rendered and exported a synthetic PDF using the bundled text, PDF and image runtimes.
- The per-user installer passed install, packaged startup with a restricted PATH, reinstallation and uninstall. A test PDF inside the installation tree survived reinstallation and uninstall. The host already had developer tools, so this test leaves the clean-machine gate open.
- The [performance report](PERFORMANCE_REPORT.md) records actual timing and working-set results through 500 pages and 20 consecutive jobs.

## Release gates still open

- A disconnected clean Windows 10 and 11 standard-user VM is needed for installation and native Explorer drag and drop, clipboard, and high-DPI acceptance.
- GitHub Actions needs an authorized hosted run. Live private-repository credentials, a production release key and an authorized test release are needed to verify two-version update installation and settings preservation end to end.
- Thai localization covers primary labels. Additional interface messages and the user guide still need Thai translations.

## Artifacts

The installer and SHA-256 checksum are generated under `dist`. The local installer is unsigned and has no embedded production release key. The [user guide](USER_GUIDE.md) explains installation and local PDF workflows. The [release guide](RELEASE_GUIDE.md) and [update setup guide](UPDATER_SETUP.md) describe CI, verification keys and publishing. The [security review](SECURITY_REVIEW.md) records the privacy boundaries.
