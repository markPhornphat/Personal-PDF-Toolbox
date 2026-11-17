"""Local PDF services. PDFium calls are serialized across viewer and export jobs."""

from __future__ import annotations

import io
import math
import os
import re
from collections.abc import Callable, Iterable, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, RLock
from zipfile import ZIP_DEFLATED, ZipFile

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter

MAX_PIXELS = 32_000_000
_PDFIUM = RLock()
Progress = Callable[[int, int], None]


class Cancelled(Exception):
    """Cancellation requested before publishing outputs."""


class PasswordRequired(ValueError):
    """The file requires a password."""


@dataclass(frozen=True)
class Page:
    path: Path
    index: int
    password: str = field(default="", repr=False)
    rotation: int = 0


@dataclass(frozen=True)
class BlankPage:
    width: int = 595
    height: int = 842
    rotation: int = 0


PageReference = Page | BlankPage


def safe_local(path: Path) -> bool:
    if os.name != "nt":
        return True
    import ctypes
    import stat

    absolute = Path(os.path.abspath(path))
    root = absolute.anchor
    if root.startswith("\\\\") or ctypes.windll.kernel32.GetDriveTypeW(root) not in {
        2,
        3,
        5,
        6,
    }:
        return False
    current = Path(root)
    for part in absolute.parts[1:]:
        current /= part
        try:
            info = current.lstat()
        except FileNotFoundError:
            return True
        except OSError:
            return False
        if info.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            return False
    return True


def check_cancelled(event: Event | None) -> None:
    if event is not None and event.is_set():
        raise Cancelled()


def page_range(selection: str, count: int) -> list[int]:
    result = []
    seen = set()
    for part in selection.split(","):
        match = re.fullmatch(r"([0-9]+)(?:\s*-\s*([0-9]+))?", part.strip())
        if not match:
            raise ValueError("Enter page numbers or ranges such as 1-3,5.")
        start = int(match[1])
        end = int(match[2] or match[1])
        if not 1 <= start <= end <= count:
            raise ValueError(f"Each range must be in ascending order within pages 1–{count}.")
        for index in range(start - 1, end):
            if index in seen:
                raise ValueError("Page ranges must not overlap or repeat a page.")
            seen.add(index)
            result.append(index)
    return result


def split_groups(mode: str, value: str, count: int) -> list[list[int]]:
    if count < 1:
        raise ValueError("Add a PDF before splitting.")
    if mode == "Custom ranges":
        groups = [page_range(group, count) for group in value.split(";")]
        if len({page for group in groups for page in group}) != sum(map(len, groups)):
            raise ValueError("Split groups must not overlap.")
        return groups
    if mode == "Boundaries":
        stops = sorted(index + 1 for index in page_range(value, count - 1))
    else:
        step = int(value) if mode == "Every N pages" and value.isdecimal() else 1
        if mode == "Every N pages" and (not value.isdecimal() or step < 1):
            raise ValueError("Enter a positive number of pages per file.")
        stops = list(range(step, count, step))
    edges = [0, *stops, count]
    return [list(range(first, last)) for first, last in zip(edges, edges[1:])]


def read_pdf(stream, password: str) -> PdfReader:
    reader = PdfReader(stream)
    if reader.is_encrypted and not reader.decrypt(password):
        raise PasswordRequired("Enter the password for this PDF.")
    return reader


def inspect(path: Path, password: str = "") -> int:
    with path.open("rb") as stream:
        count = len(read_pdf(stream, password).pages)
    if not count:
        raise ValueError("This PDF has no pages.")
    return count


@contextmanager
def locked_page(reference: PageReference):
    with _PDFIUM:
        document = (
            pdfium.PdfDocument.new()
            if isinstance(reference, BlankPage)
            else pdfium.PdfDocument(reference.path, password=reference.password or None)
        )
        try:
            page = (
                document.new_page(reference.width, reference.height)
                if isinstance(reference, BlankPage)
                else document[reference.index]
            )
            try:
                yield page
            finally:
                page.close()
        finally:
            document.close()


def page_size(reference: PageReference) -> tuple[float, float]:
    with locked_page(reference) as page:
        width, height = page.get_size()
    return (height, width) if reference.rotation % 180 else (width, height)


def dimensions(reference: Page, dpi: int) -> tuple[int, int]:
    width, height = page_size(reference)
    return math.ceil(width * dpi / 72), math.ceil(height * dpi / 72)


def render(
    reference: PageReference,
    *,
    pixels: int | None = None,
    dpi: int = 200,
    transparent: bool = False,
) -> Image.Image:
    with locked_page(reference) as page:
        width, height = page.get_size()
        if min(width, height) <= 0:
            raise ValueError("This page has invalid dimensions.")
        scale = pixels / max(width, height) if pixels else dpi / 72
        if math.ceil(width * scale) * math.ceil(height * scale) > MAX_PIXELS:
            raise ValueError("The output image is too large. Choose a lower DPI.")
        bitmap = page.render(
            scale=scale,
            rotation=reference.rotation,
            fill_color=(255, 255, 255, 0 if transparent else 255),
            force_bitmap_format=pdfium.raw.FPDFBitmap_BGRA if transparent else None,
        )
        try:
            return bitmap.to_pil().copy()
        finally:
            bitmap.close()


def convert(reference: Page, fmt: str, dpi: int, quality: int, transparent: bool = False) -> bytes:
    if fmt not in {"JPEG", "PNG"} or not 1 <= dpi <= 2400 or not 1 <= quality <= 100:
        raise ValueError("Choose a supported output format, DPI and quality.")
    image = render(reference, dpi=dpi, transparent=transparent and fmt == "PNG")
    if fmt == "JPEG":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format=fmt, dpi=(dpi, dpi), quality=quality)
    return buffer.getvalue()


def write_pdf(
    pages: Sequence[PageReference],
    destination: Path,
    cancelled: Event | None = None,
    progress: Progress | None = None,
    overlays: dict[int, bytes] | None = None,
) -> None:
    if not pages:
        raise ValueError("An output PDF needs at least one page.")
    writer = PdfWriter()
    with ExitStack() as stack:
        readers = {}
        for index, reference in enumerate(pages):
            check_cancelled(cancelled)
            if isinstance(reference, BlankPage):
                output = writer.add_blank_page(reference.width, reference.height)
            else:
                key = reference.path, reference.password
                if key not in readers:
                    stream = stack.enter_context(reference.path.open("rb"))
                    readers[key] = read_pdf(stream, reference.password)
                reader = readers[key]
                if overlays and index in overlays:
                    writer.reset_translation(reader)
                output = writer.add_page(reader.pages[reference.index], excluded_keys=("/AA",))
            if reference.rotation:
                output.rotate(reference.rotation)
            if overlays and index in overlays:
                stamp = PdfReader(io.BytesIO(overlays[index]))
                writer.pdf_header = max(writer.pdf_header, stamp.pdf_header)
                output.merge_transformed_page(stamp.pages[0], overlay_transform(output))
            if progress:
                progress(index + 1, len(pages))
        writer.write(destination)


def overlay_transform(page) -> tuple[float, float, float, float, float, float]:
    left, bottom, right, top = map(float, page.cropbox)
    media_left, media_bottom, media_right, media_top = map(float, page.mediabox)
    left, bottom = max(left, media_left), max(bottom, media_bottom)
    right, top = min(right, media_right), min(top, media_top)
    return {
        0: (1, 0, 0, 1, left, bottom),
        90: (0, 1, -1, 0, right, bottom),
        180: (-1, 0, 0, -1, right, top),
        270: (0, -1, 1, 0, left, top),
    }[page.rotation % 360]


def publish(
    folder: Path,
    names: Sequence[str],
    produce: Callable[[int, Path], None],
    cancelled: Event | None = None,
    archive: str | None = None,
) -> list[Path]:
    output_names = [archive] if archive else list(names)
    for name in [*names, *output_names]:
        if (
            not name
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.endswith((" ", "."))
            or re.fullmatch(
                r"(?i:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", name.split(".")[0].rstrip()
            )
        ):
            raise ValueError("Choose a valid Windows output filename.")
    if len({name.casefold() for name in names}) != len(names):
        raise ValueError("Choose a filename pattern that produces unique names.")
    targets = [folder / name for name in output_names]
    if any(target.exists() for target in targets):
        raise FileExistsError("An output file already exists. Choose a new name or folder.")
    with TemporaryDirectory(dir=folder, prefix=".pdf-toolbox-") as temporary:
        stage = Path(temporary)
        files = [stage / f"{index}.part" for index in range(len(names))]
        for index, path in enumerate(files):
            check_cancelled(cancelled)
            produce(index, path)
        if archive:
            zipped = stage / "output.zip"
            with ZipFile(zipped, "w", ZIP_DEFLATED) as package:
                for name, path in zip(names, files, strict=True):
                    check_cancelled(cancelled)
                    package.write(path, name)
            files = [zipped]
        check_cancelled(cancelled)
        placed = []
        try:
            for path, target in zip(files, targets, strict=True):
                if os.name == "nt":
                    path.rename(target)
                else:
                    os.link(path, target)
                placed.append(target)
        except OSError:
            for target in placed:
                target.unlink(missing_ok=True)
            raise
    return targets


def export(
    pages: Iterable[PageReference],
    output: Path,
    *,
    cancelled: Event | None = None,
    progress: Progress | None = None,
    overlays: dict[int, bytes] | None = None,
) -> Path:
    ordered = list(pages)
    return publish(
        output.parent,
        [output.name],
        lambda _, path: write_pdf(ordered, path, cancelled, progress, overlays),
        cancelled,
    )[0]
