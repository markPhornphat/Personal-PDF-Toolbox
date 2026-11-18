# Batch PDF to Word Implementation Plan

**Goal:** Append ordered PDF page images to a copy of an existing Word document, locally.

**Architecture:** Reuse PDFium/Pillow rendering and Qt Jobs. Add a lazy pywin32 COM adapter, pure placement models, a transactional conversion service, and a dedicated Qt panel. Preserve the updater and existing tool indices.

**Spec:** User's attached Batch PDF to Word Automation specification.

## Constraints and design choices

- Process locally; never save edits to the source. Stage output beside the destination.
- Use isolated Word instances with macros disabled and explicit cleanup.
- Retain final-section settings, use page breaks and embedded floating images anchored to new paragraphs.
- Verify actual Word pagination, image anchors, geometry, source hash, original content and section/header/footer snapshots before publication and after reopen.
- Fail closed for layouts whose geometry cannot be measured, rather than claim protection.
- Reuse PDFium rather than adding PyMuPDF. Only pywin32 is added.
- Keep a schematic, bounded preview; accurate pagination comes from Word inspection.
- Overwrite an existing output only with explicit GUI confirmation; never overwrite any input.

## Tasks

- [x] Add failing pure layout and transaction tests: aspect ratios, alignment, clipping, ordering, cancellation, source/output protection, failed validation.
- [x] Implement `word_layout.py` models, safe rectangles, settings, natural ordering and validation.
- [x] Implement `word_com.py` inspection, isolated COM lifecycle, append, measurement, preservation and reopen validation. Latest changes require execution.
- [x] Implement `word_conversion.py` bounded sequential rendering, detailed progress, staged publication and cleanup. Latest changes require execution.
- [x] Add `word_ui.py` intake/order/settings/preview/output/progress/results, integrate sidebar without changing existing tool indices. GUI verification remains pending.
- [ ] Add real Word integration tests and workload benchmark tooling. Execute available tests; record limitations honestly.
- [x] Update packaging, README, changelog, architecture, feature matrix, guide and test report.
- [ ] Run locked sync, Ruff, mypy and pytest, then package and smoke-test.

## Review focus

Trailing breaks/tables must retain the original page count and append precisely one page per image. Large headers, floating objects and unavailable geometry must fail safely. Cancel and validation errors must leave existing outputs intact. Aliased source/output paths must be rejected. User Word sessions must remain untouched.

The user authorized pushing to main and publishing the release on 2026-11-18.

## Execution ledger

- Existing architecture and optional skills inspected; no replacement renderer or updater was introduced.
- Locked Windows environment synced after pinning pywin32 311.
- Six initial pure tests passed. Initial Ruff and mypy checks passed after unused-import cleanup.
- Real Word tests exposed a keyword-anchor COM issue; explicit positional anchors resolved that check.
- Synthetic diagnostics showed Word save-session IDs and inactive empty-header normalization. Ruling: retain the original OOXML package and merge only appended Word-generated nodes/media, then reopen and validate — this preserves original parts instead of accepting incidental Word rewrites.
- Review findings addressed: preserve original resources, fail closed for uncertain footer tables, recheck original locks, restore the Word link-update option, and validate original page boundaries.
- Latest tests, formatting, full regression suite, screenshots, real Word acceptance, benchmarks and packaging remain blocked: unified process creation fails with Windows access denied (5), and Node runtime launch fails with device error (31).
- No final release-quality or definition-of-done claim is made. See the feature test report for exact observed evidence.

### Release verification follow-up

- Process execution recovered. Fixed mypy DOM root nullability/type inference, formatted new files, and reran the locked environment and all checks.
- Ruff, formatting and mypy passed; standard suite: 50 passed, four opt-in skipped. Opt-in real Word suite: four passed, including the final package assembly.
- Version bumped to 0.3.0. Installer build and bundled startup passed. Local install/uninstall test stopped safely because this profile already has the app installed; the clean release runner handles installer acceptance.
- GitHub write access restored by the user signing in as the repository owner. Release preparation and independent review continue before push.
