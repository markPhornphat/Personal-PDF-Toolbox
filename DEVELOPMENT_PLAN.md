# PDF Toolbox development plan

1. Lock the Windows x64 Python and native dependencies. Exercise PDFium rendering and Qt PDF generation on local synthetic PDFs.
2. Implement and test page selection, nondestructive PDF exports, image rendering, and cancellation with staged outputs.
3. Connect the dashboard, page workspace and editor to those services. Exercise clipboard, reordering and output placement in Qt tests.
4. Build the one-directory application and per-user installer. Smoke test installation, startup and removal where available.
5. Isolate GitHub update access and verify signed manifests and installer bytes. Add build and release workflows, with publication controlled by the repository owner.
6. Record verified behavior and remaining release gates in the feature matrix and test report. Defer P1 and P2 until P0 meets its acceptance criteria.
