# Performance report

Measured locally on Windows 11 x64 build 26300 with CPython 3.12.16. The benchmark uses synthetic mixed-size blank documents and an image-heavy fixture. Peak working set is cumulative over the process lifetime.

| Operation | Elapsed | Working set after | Process peak so far |
| --- | ---: | ---: | ---: |
| Export 10 mixed-size pages | 0.007 s | 39.8 MiB | 39.8 MiB |
| Export 100 mixed-size pages | 0.023 s | 40.5 MiB | 40.5 MiB |
| Export 500 mixed-size pages | 0.129 s | 43.0 MiB | 43.0 MiB |
| Image-heavy page to JPG at 600 DPI | 0.263 s | 48.8 MiB | 244.2 MiB |
| 20 consecutive previews and PDF exports | 0.160 s | 49.1 MiB | 244.2 MiB |

The consecutive-job median was 0.007 s. Working set went from 48.8 MiB to 49.1 MiB over the loop. Large raster output was the highest memory operation measured. Actual performance will vary with page content and hardware.

Reproduce with `uv run --locked python scripts/benchmark.py`. Long-run GUI responsiveness, repeated editor instrumentation and concurrent updates remain unmeasured.
