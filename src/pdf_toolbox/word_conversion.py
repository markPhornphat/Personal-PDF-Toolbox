"""Offline, bounded PDF rendering and transactional Word output."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Event
import time

from .pdf import Page, check_cancelled, inspect, render, safe_local
from .word_layout import PlacementSettings
from .word_logging import record_error


@dataclass(frozen=True)
class PDFInput:
    path: Path
    pages: int
    size: int


@dataclass(frozen=True)
class WordProgress:
    stage: str
    filename: str = ""
    page: int = 0
    file_pages: int = 0
    processed: int = 0
    total: int = 0
    elapsed: float = 0


@dataclass(frozen=True)
class WordResult:
    path: Path
    original_pages: int
    pdf_files: int
    added_pages: int
    final_pages: int
    elapsed: float


def digest(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def pdf_inputs(paths: Sequence[Path]) -> list[PDFInput]:
    result = []
    seen: set[Path] = set()
    for raw in paths:
        path = Path(raw).resolve()
        if path in seen:
            raise ValueError(f"Duplicate PDF: {path.name}")
        if not safe_local(path) or path.suffix.lower() != ".pdf":
            raise ValueError(f"Choose a local PDF file: {path.name}")
        try:
            pages = inspect(path)
        except Exception as error:
            raise ValueError(
                f"{path.name}: invalid, inaccessible or password-protected PDF."
            ) from error
        result.append(PDFInput(path, pages, path.stat().st_size))
        seen.add(path)
    return result


def generate(
    inputs: Sequence[PDFInput],
    source: Path,
    output: Path,
    settings: PlacementSettings,
    cancelled: Event | None = None,
    progress: Callable[[WordProgress], None] | None = None,
    *,
    overwrite: bool = False,
    backend=None,
) -> WordResult:
    from .word_com import WordAutomation, check_document

    started = time.monotonic()
    source, output = source.resolve(), output.resolve()
    if (
        not safe_local(source)
        or not safe_local(output)
        or source.suffix.lower() != ".docx"
        or output.suffix.lower() != ".docx"
    ):
        raise ValueError("Choose local .docx input and output files.")
    protected = [source, *(item.path.resolve() for item in inputs)]
    if output in protected or any(
        output.exists() and path.exists() and os.path.samefile(output, path) for path in protected
    ):
        raise ValueError("The output must be separate from every input file.")
    if not inputs:
        raise ValueError("Add at least one PDF.")
    if output.exists() and not overwrite:
        raise FileExistsError(
            "The output already exists. Confirm overwrite or choose another name."
        )
    output_hash = digest(output) if overwrite and output.exists() else None
    check_cancelled(cancelled)
    if backend is None:
        check_document(source)
    hashes = {path: digest(path) for path in protected}
    validated = pdf_inputs([item.path for item in inputs])
    total = sum(item.pages for item in validated)
    # Fail before launching Word if the destination is inaccessible.
    with TemporaryDirectory(prefix=".word-", dir=output.parent) as temporary:
        folder = Path(temporary)
        staged = folder / "working.docx"
        shutil.copy2(source, staged)

        def report(stage, item=None, page=0, processed=0):
            if progress:
                progress(
                    WordProgress(
                        stage,
                        item.path.name if item else "",
                        page,
                        item.pages if item else 0,
                        processed,
                        total,
                        time.monotonic() - started,
                    )
                )

        report("Opening Word")
        with (backend or WordAutomation)() as word:
            original = word.open(staged)
            processed = 0
            for item in validated:
                for page in range(item.pages):
                    check_cancelled(cancelled)
                    report("Rendering PDF", item, page + 1, processed)
                    image_path = folder / ("page.jpg" if settings.format == "JPEG" else "page.png")
                    try:
                        with render(
                            Page(item.path, page), dpi=settings.dpi, max_pixels=64_000_000
                        ) as image:
                            image.save(
                                image_path,
                                format=settings.format,
                                quality=settings.quality,
                                dpi=(settings.dpi, settings.dpi),
                            )
                        check_cancelled(cancelled)
                        report("Appending Word page", item, page + 1, processed)
                        word.append(image_path, settings, original + processed + 1)
                    except Exception as error:
                        from .pdf import Cancelled

                        if isinstance(error, Cancelled):
                            raise
                        record_error("PDF render or Word page insertion", error)
                        raise ValueError(f"{item.path.name}, page {page + 1}: {error}") from error
                    finally:
                        image_path.unlink(missing_ok=True)
                    processed += 1
                    report("Page appended", item, page + 1, processed)
            check_cancelled(cancelled)
            report("Validating and reopening", processed=processed)
            word.validate_save(original + total, total)
        check_cancelled(cancelled)
        if any(digest(path) != expected for path, expected in hashes.items()):
            raise ValueError("An input changed during processing. No output was published.")
        if any(
            output.exists() and path.exists() and os.path.samefile(output, path)
            for path in protected
        ):
            raise ValueError("The output now refers to an input file. No output was published.")
        # Destination state is checked again after the potentially long COM operation.
        if overwrite:
            current_output_hash = digest(output) if output.exists() else None
            if current_output_hash != output_hash:
                raise FileExistsError(
                    "The output changed during processing. "
                    "Choose another filename or confirm it again."
                )
            os.replace(staged, output)
        else:
            # On Windows rename is atomic and refuses an existing destination.
            os.rename(staged, output)
    return WordResult(
        output, original, len(validated), total, original + total, time.monotonic() - started
    )
