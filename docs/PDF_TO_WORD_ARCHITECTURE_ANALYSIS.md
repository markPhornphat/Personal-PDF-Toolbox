# PDF to Word: repository analysis

Inspected 2026-11-18, before feature implementation. Baseline commit:
`36c7a4cf78551e3fb8711740e80fc789328e9a12`.

## Existing application

This repository is a Windows x64 Python 3.12 / PySide6 Essentials application,
with six existing PDF tools rather than a standalone image converter.
`src/main.py` starts `pdf_toolbox.app.Window`. The window builds the dashboard,
sidebar, stacked tool panels, shared theme, preferences, local intake and dialogs.
`workspace.py` owns page lists and the image export controls; `viewer.py` renders
previews asynchronously. Existing tools must retain their ordering and behavior.

`pdf.py` uses pypdf for structural reads/writes and PDFium for rasterization.
`Page(path, index)` identifies a page, `inspect(path)` counts pages and rejects
empty PDFs, and `read_pdf` handles encryption. `render` serializes PDFium access
through an `RLock`, observes crop/rotation through PDFium, returns a copied Pillow
image and closes native PDF/document/bitmap resources. `convert` produces JPEG or
PNG bytes with DPI metadata. JPEG is rendered on white; transparent PNG is optional.
Rendering rejects images larger than 32 million pixels. At 600 DPI, some normal
paper sizes exceed that cap; the UI must explain a request to lower DPI rather
than silently claim the requested resolution was used.

`pdf.publish` validates local Windows output names, stages files in a temporary
directory inside the destination, checks cancellation before publication and
refuses existing targets. Its all-new-output policy cannot directly provide the
requested explicit overwrite option for Word outputs.

## Reusable services and boundaries

- Reuse `Page`, `inspect`, `render`/`convert`, `check_cancelled`, `Cancelled` and
  `safe_local`; do not add PyMuPDF to duplicate the existing raster engine.
- Reuse `Jobs`, whose QRunnable workers own cancellation events. Qt signals return
  progress and completion to the GUI thread. Initialize/uninitialize COM inside
  each worker that uses Word; never pass live COM documents between threads.
- Reuse the appearance system and local file/drop conventions. Add a dedicated
  PDF-to-Word panel so page-workspace tools do not inherit Word-specific state.
- Keep Word layout calculation independently testable. The same geometry should
  drive schematic preview and COM positioning.
- Keep Word automation optional and lazily imported. The existing image tools
  must start and work when Word or COM automation is unavailable.

## Word-specific design constraints

The current dependency `pywin32-ctypes` implements updater credential support;
it does not provide Word COM automation. Add the real `pywin32` package, keep the
Windows lockfile reproducible, and include `pythoncom`, `pywintypes` and
`win32com.client` in packaging. Word Desktop remains an external prerequisite.
Use an isolated Word instance, disable document macro execution within that
instance, suppress unnecessary dialogs, and release only application-owned COM
resources. Never terminate a user's Word process.

Inspect a temporary copy read-only with Word's pagination engine. Generate into
a fresh staged copy and publish only after repagination, page/image/order/layout
checks, successful reopen and input integrity checks. File hashes protect source
bytes; they cannot prove the rendered original pages stayed unchanged. Preserve
section and header/footer structures and report uncertainty honestly. Header
distance alone is not an occupied header boundary. Tall tables, floating logos,
first/even/odd headers, gutter, mirrored margins and unusual trailing content
require real Word fixtures and conservative rejection when safety is unknown.

## Updates and packaging

`updater.py` owns GitHub HTTPS access, signed manifests, verified downloads and
Windows credentials. `settings.py` stores explicit automatic-check consent.
`app.py.check_updates` returns before network work when automatic checks are not
enabled. Conversion workers have no reason to import or call the updater.

`scripts/build.ps1` generates version metadata, builds through PyInstaller,
executes a hidden packaged startup smoke test and compiles the per-user Inno
Setup installer. `packaging/pdf-toolbox.spec` bundles fonts, resources, licenses
and optional update configuration. `pyproject.toml` supplies version metadata.
Run `uv sync --locked`, Ruff, mypy and pytest before building. A build on the
development workstation is not proof of operation on a machine without Python;
that acceptance test must remain pending until performed. Pushing or publishing
requires separate authorization.

## Understand Anything analysis artifact

The requested skill was read and its installed built runtime was found at
`C:/Users/Mark/.understand-anything/repo/understand-anything-plugin`.
The bundled deterministic scanner inspected 49 baseline files with no ignore
exclusions. `.ua/intermediate/scan-result.json` records the inventory.
`.ua/knowledge-graph.json` is explicitly a **partial, file-level architecture
graph** derived from that inventory and Python imports. It is not a completed
semantic symbol graph. Full multi-agent symbol analysis, fingerprints, dashboard
launch and auto-update metadata were not produced during feature implementation.
