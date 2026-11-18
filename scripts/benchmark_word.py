"""Opt-in synthetic Word benchmark. Run on Windows with activated Word Desktop.

No user documents or network services are used. Results are JSON, never estimated.
CPU covers Python and the owned Word instance; RAM is the sum of process peak
working sets (an upper bound, not a synchronized combined peak).
"""

import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pypdf import PdfWriter
from pdf_toolbox.word_com import WordAutomation
from pdf_toolbox.word_conversion import generate, pdf_inputs
from pdf_toolbox.word_layout import PlacementSettings


class MemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        *[
            (name, ctypes.c_size_t)
            for name in (
                "PeakWorkingSetSize",
                "WorkingSetSize",
                "QuotaPeakPagedPoolUsage",
                "QuotaPagedPoolUsage",
                "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage",
                "PagefileUsage",
                "PeakPagefileUsage",
            )
        ],
    ]


def metrics(handle):
    creation, exit_time, kernel, user = (wintypes.FILETIME() for _ in range(4))
    if not ctypes.windll.kernel32.GetProcessTimes(
        handle,
        ctypes.byref(creation),
        ctypes.byref(exit_time),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError()
    memory = MemoryCounters()
    memory.cb = ctypes.sizeof(memory)
    if not ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
        raise ctypes.WinError()
    cpu = (
        sum((value.dwHighDateTime << 32) + value.dwLowDateTime for value in (kernel, user))
        / 10_000_000
    )
    return cpu, memory.PeakWorkingSetSize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=int, nargs="+", default=[10, 25, 50, 100, 200])
    parser.add_argument("--output", type=Path, default=Path("build/word-benchmark.json"))
    args = parser.parse_args()
    kernel = ctypes.windll.kernel32
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, *[ctypes.POINTER(wintypes.FILETIME)] * 4]
    ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(MemoryCounters),
        wintypes.DWORD,
    ]
    ctypes.windll.user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    results = []
    for count in args.pages:
        with TemporaryDirectory(prefix="pdf-toolbox-word-benchmark-") as temporary:
            root = Path(temporary)
            source = root / "source.docx"
            with WordAutomation() as word:
                word.doc = word.app.Documents.Add()
                word.doc.Content.Text = "Original benchmark page"
                word.doc.SaveAs2(str(source), FileFormat=16)
            pdf = root / "pages.pdf"
            writer = PdfWriter()
            for _ in range(count):
                writer.add_blank_page(595, 842)
            writer.write(pdf)
            owned = {}

            class MeasuredWord(WordAutomation):
                def open(self, path):
                    result = super().open(path)
                    pid = wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        self.doc.ActiveWindow.Hwnd, ctypes.byref(pid)
                    )
                    owned["handle"] = kernel.OpenProcess(0x410, False, pid.value)
                    owned["cpu_start"], _ = metrics(owned["handle"])
                    return result

                def __exit__(self, *values):
                    try:
                        if owned.get("handle"):
                            cpu, ram = metrics(owned["handle"])
                            owned["cpu_seconds"] = cpu - owned["cpu_start"]
                            owned["peak_ram_bytes"] = ram
                    finally:
                        if owned.get("handle"):
                            kernel.CloseHandle(owned["handle"])
                        super().__exit__(*values)

            stages = {}
            last = [None, time.perf_counter()]

            def progress(value):
                now = time.perf_counter()
                if last[0]:
                    stages[last[0]] = stages.get(last[0], 0) + now - last[1]
                last[:] = [value.stage, now]

            cpu_before, _ = metrics(kernel.GetCurrentProcess())
            started = time.perf_counter()
            result = generate(
                pdf_inputs([pdf]),
                source,
                root / "output.docx",
                PlacementSettings(),
                progress=progress,
                backend=MeasuredWord,
            )
            elapsed = time.perf_counter() - started
            stages[last[0]] = stages.get(last[0], 0) + time.perf_counter() - last[1]
            cpu_after, ram = metrics(kernel.GetCurrentProcess())
            record = {
                "pages": count,
                "total_seconds": elapsed,
                "render_seconds": stages.get("Rendering PDF", 0),
                "word_insert_seconds": stages.get("Appending Word page", 0),
                "validate_reopen_publish_seconds": stages.get("Validating and reopening", 0),
                "average_cpu_percent_of_one_core": 100
                * (cpu_after - cpu_before + owned["cpu_seconds"])
                / elapsed,
                "peak_ram_upper_bound_bytes": ram + owned["peak_ram_bytes"],
                "output_bytes": result.path.stat().st_size,
                "workload": "blank portrait A4 PDF, 300 DPI JPEG; synthetic baseline only",
            }
            results.append(record)
            print(json.dumps(record), flush=True)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
