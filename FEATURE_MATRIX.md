# Feature matrix

| Feature | Priority | Implementation | Verification | Remaining work | Version |
| --- | --- | --- | --- | --- | --- |
| Merge and append | P0 | Document cards, page order, range insertion, duplicate, remove, undo and redo | Reordered PDF output and source preservation | Native Explorer and page-drag acceptance | 0.1.0 |
| Split PDF | P0 | Individual pages, fixed-size groups, ranges, boundaries, visual split markers and ZIP | Range validation, boundary grouping and GUI output | Native drag selection and large batches | 0.1.0 |
| Remove and extract pages | P0 | Multi-select, reorder, remove, separate or combined extraction | GUI extraction and zero-page protection in service | Native modifier-key and drag acceptance | 0.1.0 |
| PDF to JPG and PNG | P0 | Page selection, batch input, DPI, JPG quality, transparency, size estimate and ZIP | GUI PNG output, transparency and 600 DPI JPG benchmark | Broad corpus and color-fidelity checks | 0.1.0 |
| PDF editor | P0 | Text, images, shapes, movement, resizing, rotation, object layers and history | Vector export, four rotations, cropped placement and screenshot paste | High-DPI manual testing and wider Thai typography corpus | 0.1.0 |
| Drag and drop, clipboard, viewer | P0 | File intake, image/text paste, page thumbnails, zoom, fit and pan | Qt file-drop and clipboard workflows, GUI tests at 2× scaling | Windows Explorer, native keyboard and pointer acceptance | 0.1.0 |
| Localization and preferences | P0 | English interface, Thai primary labels, Thai paths and editable text, themes and persistent defaults | Thai PDF text and Unicode input path tests | Remaining Thai labels, messages and help | 0.1.0 |
| Per-user offline installer | P0 | PyInstaller bundle and Inno Setup executable | See the test report for installer checks | Disconnected clean Windows 10 and 11 VM acceptance | 0.1.0 |
| GitHub CI and release | P0 | Windows test, installer and signed manifest workflow | Local build scripts and automated tests | Authorized hosted run and publishing rehearsal | 0.1.0 |
| Update manager | P0 | Opt-in checks, Ed25519 manifest, SHA-256, optional Windows publisher check and Credential Manager | Controlled transport, tamper rejection, download cleanup and Windows trust helper | Signed two-version rehearsal and real private repository authentication | 0.1.0 |
| Additional PDF utilities | P1/P2 | Pending the P0 release gate | Pending | See master specification | — |
