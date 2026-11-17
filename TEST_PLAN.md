# Test plan

Run the automated suite under Qt's offscreen platform. It creates synthetic PDFs and images as fixtures.

- Exercise ordered page copy, duplicates, ranges, password handling, image transparency, cancellation and no-clobber writes.
- Exercise the five normal Qt workspace export paths and compare exported results against known fixture pages. Test pasted screenshot pixels, undo, vector text and overlay placement on cropped pages at each rotation.
- Test stable version comparisons, signed manifest and installer verification, redirect boundaries, interrupted downloads and invalid metadata through a controlled transport.
- Build and launch the one-directory executable, install to a disposable per-user directory, repeat the startup with a restricted PATH, and uninstall.
- Run a separate clean-machine acceptance pass on disconnected Windows 10 and 11 x64 with a standard user. Exercise native Explorer drag and drop, clipboard, high-DPI interaction, all P0 tools and upgrade settings.
- Run a two-version signed release rehearsal in a controlled authorized environment. Verify authentic-update consent, offline recovery, installer failure handling and settings preservation.
- Use the performance script for 10-, 100- and 500-page synthetic PDFs, image-heavy 600 DPI output and consecutive jobs. Record timing and memory alongside the machine context.
