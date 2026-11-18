# PDF to Word verification report

Date: 2026-11-18. Version: 0.3.0. The locked environment, Ruff, formatting, mypy, all 50 standard tests and four opt-in real Word integration tests passed. The installer build and bundled startup passed. Broader document-corpus and clean-machine acceptance are listed separately below.

## Evidence observed

| Check | Observed result | Scope |
| --- | --- | --- |
| Locked environment | `uv sync --locked --cache-dir .uv-cache` succeeded after pywin32 lock update | Windows Python 3.12 environment |
| Pure service tests | 6 passed in 0.79 s | Initial layout/transaction implementation: alignment, fit cap, bad settings, natural sorting, PDF validation/order/duplicates, staged output, overwrite rejection, validation rollback, cancellation and source alias protection |
| Ruff and formatting | Passed | `ruff check src tests scripts` and `ruff format --check src tests scripts` |
| mypy | Passed, 20 source files | `mypy --ignore-missing-imports src`; nullable DOM roots and relationship-map typing corrected |
| Full standard suite | 50 passed, 4 skipped in 5.51 s | All current service, package, GUI, PDF/editor/localization/updater regressions; only real Word cases skipped by default |
| Opt-in real Word suite | 4 passed in 72.08 s | Text, table and trailing-break document endings; portrait/landscape PDF pages, reopen/page count/source hashes and cancellation |
| Windows installer build | Passed | Existing PyInstaller/Inno Setup build and bundled startup, including COM imports |
| Local install/uninstall smoke | Not run: script's safety check stopped it | This user profile already has PDF Toolbox installed; clean GitHub runner must perform this check |
| Word panel screenshot | Captured and visually inspected | `artifacts/screenshots/pdf-to-word.png`, synthetic local documents |
| Existing native Qt regression run inside restricted desktop | 27 passed, 5 failed | Clipboard and desktop access failures plus missing new navigation tooltip; tooltip subsequently fixed |
| Existing Qt regression offscreen | First 11 passed; navigation tooltip failed, then fixed | Next run progressed through 14 cases but did not finish; interrupted |
| Real Word execution | Word available through approved desktop execution | Sandbox COM activation was denied; isolated Word test runs executed outside that restriction |
| Initial real Word test | Failed: first image anchor moved to page 1 | Fixed by explicit positional COM anchor argument; subsequent run passed anchor validation |
| Subsequent real Word test | Failed preservation comparison | Diagnostic synthetic fixtures showed save-session IDs and Word pruning/reassigning inactive empty header parts |
| Final package strategy | Original package retained; appended nodes and media merged with fresh relationship IDs | Package unit test and four real Word cases passed |
| Earlier process execution failure | Recovered before release preparation | Previously blocked PowerShell/Node launches; latest commands executed successfully |

Earlier failed runs above are retained as diagnostic history, not outstanding failures. The final standard and real Word suites passed. Synthetic workload measurements are recorded below as they complete; a clean machine without Python or Microsoft Word has not been tested locally.

## Automated coverage present

Independent release review found no material blockers. It reviewed transactional publication, source preservation, original-package assembly, image anchoring/layout validation and packaging; its assessment does not replace test execution.

## Synthetic performance measurements

Measured on this Windows development machine with local release tasks running concurrently. Workload: one blank portrait A4 PDF, one-page Word source, 300 DPI JPEG. Identical blank images are deduplicated in the document package, so output sizes and memory are not representative of image-rich documents. Raw measurements are in `PDF_TO_WORD_BENCHMARKS.json`.

| PDF pages | Total seconds | Render seconds | Insert seconds | Validate/reopen/publish seconds | CPU % of one core | RAM upper bound MiB | Output bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | 9.71 | 0.55 | 4.01 | 3.85 | 80.3 | 447 | 13443 |
| 25 | 22.53 | 1.66 | 13.86 | 5.82 | 104.0 | 463 | 14590 |
| 50 | 57.48 | 4.44 | 39.30 | 11.19 | 100.3 | 472 | 16435 |
| 100 | 95.26 | 8.26 | 66.17 | 17.95 | 105.3 | 502 | 19986 |
| 200 | 155.27 | 16.02 | 115.17 | 21.40 | 110.2 | 621 | 27021 |

CPU combines Python and the owned Word process; Word's CPU sampling begins after opening the working document, so startup CPU is excluded. RAM is the sum of process peak working sets, an upper bound rather than a synchronized combined peak. Word insertion dominates these runs; per-page pagination is retained to catch anchor/page errors. Image-rich corpus benchmarking should precede performance optimization.

- `tests/test_word.py`: pure layout/intake, ordering, cancellation, failed-validation rollback, existing-output protection and source preservation using a fake Word adapter.
- Cancellation-during-validation and concurrent-output-edit rollback cases passed in the final standard suite.
- `tests/test_word_package.py`: source styles/header/media retention and collision-safe appended image relationships.
- `tests/test_word_ui.py`: sidebar entry, PDF metadata/order/sort/remove/clear, bounded preview, settings and inspection errors.
- `tests/test_word_integration.py`: real Word reopen/page counts for text, table and trailing-break document endings, portrait/landscape PDF pages, source hashing and cancellation. Opt-in via `PDF_TOOLBOX_WORD_TESTS=1`.
- Existing PDF, editor, localization and updater regression tests are retained.

## Mandatory scenario status

| Scenarios | Status |
| --- | --- |
| T01, T03, T05, T06, T12, T14, T19 | Pure/mocked coverage passed; basic real Word conversion, cancellation and GUI tests passed |
| T02, T04, T13 | Synthetic 100/200-page Word conversions completed; full 25-file/50-original-page and image-rich workloads pending |
| T07–T09, T18, T22, T26 | Layout/preservation checks implemented; broad real corpus pending. Header/footer tables and floating objects are explicitly rejected |
| T10, T11, T16 | Error paths implemented; corrupted PDF pure test passed in initial run; protected Word/missing Word acceptance pending |
| T15 | No network calls in processing services; strict disconnected real Word acceptance pending |
| T17 | PyInstaller configuration updated; final build and no-Python clean-machine acceptance pending |
| T20, T25 | Existing regression suites passed in the final standard run |
| T21, T27 | Real Word table/trailing-break ending tests passed with package assembly and reopen validation |
| T23, T24 | Isolated instance and embedding/reopen checks implemented; independent Word-session and deleted-temp-image visual acceptance pending |

## Next verification commands

Follow `docs/PDF_TO_WORD.md`. Run Ruff including formatting, mypy, all pytest cases, then the opt-in real Word suite. Expand real tests to large headers/footers, inline logos, page fields, first/odd/even variants, multiple sections, custom/mirrored/gutter layouts, protected/locked sources and an independent open Word session. Execute `scripts/benchmark_word.py` at 10, 25, 50, 100 and 200 pages. Record measured results before optimization or release qualification.

The existing packaging script passed. Clean-runner installer verification and signed publication remain part of the GitHub release workflow. Push/publication is authorized by the user; this report records test scope rather than deployment status.

## Files delivered

New implementation: `src/pdf_toolbox/word_layout.py`, `word_conversion.py`, `word_com.py`, `word_package.py`, `word_logging.py`, and `word_ui.py`.

Existing implementation/configuration changed: `src/pdf_toolbox/app.py`, `src/pdf_toolbox/pdf.py` (optional per-call pixel cap; existing defaults retained), `pyproject.toml`, `uv.lock`, and `packaging/pdf-toolbox.spec`.

New verification tools: `tests/test_word.py`, `tests/test_word_package.py`, `tests/test_word_ui.py`, `tests/test_word_integration.py`, `scripts/benchmark_word.py`, `scripts/capture_word_screenshot.py`, and the synthetic-only `scripts/word_diagnose.py`.

Documentation: README, changelog, architecture, feature matrix, the feature guide/report, `docs/PDF_TO_WORD_ARCHITECTURE_ANALYSIS.md`, and `docs/superpowers/plans/2026-11-18-pdf-to-word.md`. The requested Understand Anything analysis also produced an explicitly partial `.ua` file graph/inventory; it is not a completed symbol-level architecture index.
