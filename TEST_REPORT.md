# PDF Toolbox 0.2.0 development report

PDF Toolbox provides six local Windows GUI workspaces for merge and append, split, remove and extract, conversion to JPG and PNG, visual PDF editing, and organizing pages. The Windows x64 installer is built from the same source. See the [feature matrix](FEATURE_MATRIX.md), [dashboard](docs/screenshots/dashboard.png), [Thai dark mode](docs/screenshots/thai-dark-home.png), and [editor](docs/screenshots/editor.png).

## Verified locally

- Windows 11 x64 build 26300, CPython 3.12.16. The locked runtime uses PySide6 Essentials 6.10.2, pypdf 6.9.2, pypdfium2 5.15.2, Pillow 12.2.0, cryptography 47.0.0 and pywin32-ctypes 0.2.3.
- 32 pytest cases passed, including 20 GUI cases rerun on native Windows Qt and at 2× Qt scaling. Ruff and mypy passed and the lock resolved offline. New coverage exercised the Organize workspace from intake to export, including hand cursors, page-range and blank-page insertion, independent rotation of duplicate pages, reverse order, undo and redo, preview dimensions, and source preservation.
- The native Windows Qt app opened the supplied four-page PDF through Ctrl+V and each Home menu choice. Validation checked eight merged and reordered pages, two two-page splits, one extracted and three retained pages, four JPGs and four transparent PNGs at 72 DPI, and a saved vector edit. The original SHA-256 matched after all exports.
- The Organize workspace processed the same four-page PDF. The five-page export preserved page contents, reversed the order, included the blank A4 page, and applied the requested rotation. The source bytes matched afterward.
- The offscreen Qt tests ran all five workspace export paths and inspected the resulting PDFs and images. They covered Unicode filenames, protected input, page order and duplication, range validation, transparent PNG, file drops, file-reference paste, screenshot paste, undo and source preservation.
- The editor preserved original page rotation and matched the expected crop-relative overlay placement for 0°, 90°, 180° and 270°. A Thai clipboard sample with combining marks rendered as vector text and extracted as the original Unicode in PDFium. An undersized text box did not add a clipped line to its replacement text. Readers that ignore PDF replacement text may still extract shaped glyphs differently.
- The Thai tests switched languages without changing the selected operation or page and exercised a localized confirmation dialog. The Thai user guide is bundled. Native Windows dialog controls use the system language.
- The updater tests used an in-memory GitHub transport with a generated test key. Manifest tampering, wrong repository, altered installer, interrupted transfer, cancelled download, draft releases and disallowed redirects were exercised. A Qt test confirmed that declining an update cancels installation and that altered bytes are rejected and can be downloaded again. It verified the saved pending-version and language settings using a simulated process launch. A live token-free check against the configured public repository confirmed the no-release status.
- PyInstaller and Inno Setup built the Windows bundle and installer. The packaged startup smoke rendered and exported a synthetic PDF using the bundled text, PDF and image runtimes.
- The 0.2.0 installer compiled and matched its SHA-256 file. The native Windows startup check loaded the mascot and exercised PDF rendering and export. The installer embeds the established public updater configuration. The 0.2.0 upgrade still needs a separate test profile.
- The 0.1.1 installer previously passed per-user install, reinstallation and uninstall. The native Windows Qt platform passed a separate `0.1.0` to `0.1.1` upgrade with Thai setup. A test file in the install tree survived both upgrade and uninstall.
- The [performance report](PERFORMANCE_REPORT.md) records actual timing and working-set results through 500 pages and 20 consecutive jobs.

## Release gates still open

- A disconnected clean Windows 10 and 11 standard-user VM is needed for installation and native Explorer drag and drop, clipboard, and high-DPI acceptance.
- A private test repository with GitHub Actions write access and a dedicated test key is needed for the live two-version rehearsal. The supplied GitHub repository is public and the connected identity can read it. The hosted workflow and private update authentication remain unverified.

## Artifacts

The installer and matching SHA-256 checksum are generated under `dist`. The local installer is unsigned and has no embedded production release key. The [English guide](USER_GUIDE.md) and [Thai guide](USER_GUIDE_TH.md) explain installation and local PDF workflows. The [release guide](RELEASE_GUIDE.md) and [update setup guide](UPDATER_SETUP.md) describe CI, verification keys and publishing. The [security review](SECURITY_REVIEW.md) records the privacy boundaries.
