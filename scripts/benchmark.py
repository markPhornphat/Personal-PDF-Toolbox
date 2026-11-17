"""Measure Windows working set and operation latency on synthetic PDFs."""

import ctypes
import io
import sys
import time
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory

from PIL import Image
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pdf_toolbox.pdf import Page, convert, export, render  # noqa: E402


class MemoryCounters(ctypes.Structure):
    _fields_ = [("size", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
        (name, ctypes.c_size_t)
        for name in (
            "peak",
            "current",
            "pool_paged_peak",
            "pool_paged",
            "pool_nonpaged_peak",
            "pool_nonpaged",
            "pagefile",
            "peak_pagefile",
        )
    ]


def usage():
    counter = MemoryCounters()
    counter.size = ctypes.sizeof(counter)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    status = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    status.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_ulong]
    if not status(kernel.GetCurrentProcess(), ctypes.byref(counter), counter.size):
        raise ctypes.WinError(ctypes.get_last_error())
    return counter.current / 2**20, counter.peak / 2**20


def measure(label, action):
    begin = time.perf_counter()
    action()
    elapsed = time.perf_counter() - begin
    current, peak = usage()
    print(f"| {label} | {elapsed:.3f} s | {current:.1f} MiB | {peak:.1f} MiB |")
    return elapsed


def make(path, count):
    writer = PdfWriter()
    for number in range(count):
        writer.add_blank_page(*((612, 792) if number % 2 else (792, 612)))
    writer.write(path)
    return [Page(path, index) for index in range(count)]


def main():
    print("| Operation | Elapsed | Working set after | Process peak so far |")
    print("| --- | ---: | ---: | ---: |")
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=artifacts) as temporary:
        folder = Path(temporary)
        for count in (10, 100, 500):
            source = make(folder / f"input-{count}.pdf", count)
            measure(
                f"Export {count} mixed-size pages",
                lambda: export(source, folder / f"output-{count}.pdf"),
            )
        out = io.BytesIO()
        Image.effect_noise((1800, 2400), 40).convert("RGB").save(out, format="PDF", resolution=300)
        heavy = folder / "image-heavy.pdf"
        heavy.write_bytes(out.getvalue())
        measure(
            "Image-heavy page to JPG at 600 DPI", lambda: convert(Page(heavy, 0), "JPEG", 600, 90)
        )
        timings = []
        small = [Page(folder / "input-10.pdf", index) for index in range(10)]
        before, _ = usage()

        def repeat():
            for index in range(20):
                start = time.perf_counter()
                render(small[index % 10], pixels=110)
                export(small, folder / f"repeat-{index}.pdf")
                timings.append(time.perf_counter() - start)

        measure("20 consecutive preview and PDF export jobs", repeat)
        after, _ = usage()
        print(
            f"\nConsecutive-job median {median(timings):.3f} s. Working set {before:.1f} to {after:.1f} MiB."
        )


if __name__ == "__main__":
    main()
