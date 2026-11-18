# Architecture

`src/main.py` starts the PySide6 application. The dashboard routes local file drops and clipboard input to a page workspace or editor. Workspaces keep document references and edit history in memory. Settings use an INI file under local application data. Recent-file tracking is absent.

- `pdf.py` uses pypdf for structural exports and PDFium for raster previews and image conversion. It serializes PDFium access and closes each document and bitmap after use. File exports stage into the selected destination before placing any output filenames.
- `jobs.py` dispatches work through Qt thread pools. The UI receives job completion and progress through Qt signals. A cancellation event is checked between units of work and before output publication.
- `viewer.py` loads the selected page asynchronously and caches a bounded set of thumbnails. `editor.py` uses PDF points in a graphics scene. Qt shapes Unicode text and generates an overlay PDF from the same drawing routine used by the canvas. The export mapper accounts for rotation and visible crop offsets.
- `updater.py` contains GitHub HTTP access, artifact verification and token storage. It has its own worker queue. PDF jobs pass no data to that subsystem.
- `pyproject.toml` is the authoritative application version. Build scripts derive the executable metadata, installer version, About display and release version from it.

Qt PDF output covers the P0 overlay requirement without ReportLab, QPDF or OCR.

The PDF-to-Word sidebar panel (`word_ui.py`) reuses Jobs and PDFium/Pillow. `word_layout.py` calculates point-based safe rectangles. `word_conversion.py` validates ordered inputs, renders one page at a time, manages cancellation and stages output. `word_com.py` creates a private thread-affine Word COM instance, inspects layout, anchors embedded images and validates pagination/geometry. `word_package.py` adds Word-generated appended paragraphs/media to the original OOXML package, preserving original parts, styles and sections. The result is reopened read-only in Word before publication. Office is required only when using this mode; COM imports are lazy. The existing updater is untouched. Verification limitations are recorded in `docs/PDF_TO_WORD_TEST_REPORT.md`.
