# Feature matrix

| Feature | Priority | Implementation | Verification | Remaining work | Version |
| --- | --- | --- | --- | --- | --- |
| Merge and append | P0 | Document cards, page order, range insertion, duplicate, remove, undo and redo | Reordered PDF output and source preservation | Native Explorer and page-drag acceptance | 0.1.0 |
| Split PDF | P0 | Individual pages, fixed-size groups, ranges, boundaries, visual split markers and ZIP | Range validation, boundary grouping and GUI output | Native drag selection and large batches | 0.1.0 |
| Remove and extract pages | P0 | Multi-select, reorder, remove, separate or combined extraction | GUI extraction and zero-page protection in service | Native modifier-key and drag acceptance | 0.1.0 |
| PDF to JPG and PNG | P0 | Page selection, batch input, DPI, JPG quality, transparency, size estimate and ZIP | GUI PNG output, transparency and 600 DPI JPG benchmark | Broad corpus and color-fidelity checks | 0.1.0 |
| PDF editor | P0 | Text, images, shapes, movement, resizing, rotation, object layers, history and Thai replacement text | Vector export, four rotations, cropped placement, screenshot paste and Thai text extraction with PDFium | Native high-DPI manual testing and wider Thai typography corpus | 0.1.1 |
| Drag and drop, clipboard, viewer | P0 | File intake, image/text paste, page thumbnails, zoom, fit and pan | Qt file-drop and clipboard workflows, GUI tests at 2× scaling | Windows Explorer, native keyboard and pointer acceptance | 0.1.0 |
| Localization and preferences | P0 | English and Thai tools, settings, prompts, messages, installer, and user guide | Live language switch, confirmation buttons, Thai paths, clipboard and PDF text | Native Windows dialogs follow the system language | 0.1.1 |
| Per-user offline installer | P0 | PyInstaller bundle and English/Thai Inno Setup executable | Fresh install and 0.1.0 to 0.1.1 upgrade on the Windows 11 development host | Disconnected clean Windows 10 and 11 VM acceptance | 0.1.1 |
| GitHub CI and release | P0 | Windows test, installer and signed manifest workflow | Local build scripts and automated tests | Authorized hosted run and publishing rehearsal | 0.1.0 |
| Update manager | P0 | Opt-in checks, Ed25519 manifest, SHA-256, optional Windows publisher check and Credential Manager | Controlled transport, consent, tamper rejection before launch, download cleanup and settings persistence at simulated launch | Live signed two-version rehearsal and private repository authentication | 0.1.1 |
| Additional PDF utilities | P1/P2 | Pending the P0 release gate | Pending | See master specification | — |
