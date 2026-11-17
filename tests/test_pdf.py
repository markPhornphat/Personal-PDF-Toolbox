import io
from threading import Event

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdf_toolbox.pdf import Cancelled, Page, convert, export, page_range, split_groups


def document(folder, name, *widths):
    path = folder / name
    writer = PdfWriter()
    for width in widths:
        writer.add_blank_page(width, 100)
    writer.write(path)
    return path


def test_ranges_and_splits():
    assert page_range("2-3,1", 3) == [1, 2, 0]
    assert split_groups("Boundaries", "2,4", 5) == [[0, 1], [2, 3], [4]]
    assert split_groups("Every N pages", "2", 5) == [[0, 1], [2, 3], [4]]
    for invalid in ("0", "4", "3-1", "1-2,2", "1,", "1--2"):
        with pytest.raises(ValueError):
            page_range(invalid, 3)


def test_export_reorders_and_duplicates_without_changing_source(tmp_path):
    source = document(tmp_path, "ต้นฉบับ.pdf", 120, 150)
    original = source.read_bytes()
    output = tmp_path / "result.pdf"
    export([Page(source, 1), Page(source, 0), Page(source, 1)], output)
    assert [page.mediabox.width for page in PdfReader(output).pages] == [150, 120, 150]
    assert source.read_bytes() == original
    with pytest.raises(FileExistsError):
        export([Page(source, 0)], source)


def test_protected_input_and_cancel(tmp_path):
    path = tmp_path / "encrypted.pdf"
    writer = PdfWriter()
    writer.add_blank_page(100, 100)
    writer.encrypt("secret", algorithm="AES-256")
    writer.write(path)
    out = tmp_path / "out.pdf"
    event = Event()
    event.set()
    with pytest.raises(Cancelled):
        export([Page(path, 0, "secret")], out, cancelled=event)
    assert not out.exists()
    export([Page(path, 0, "secret")], out)
    assert len(PdfReader(out).pages) == 1


def test_transparent_png(tmp_path):
    path = document(tmp_path, "input.pdf", 120)
    data = convert(Page(path, 0), "PNG", 144, 90, transparent=True)
    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (240, 200)
        assert image.mode == "RGBA"
        assert image.getpixel((0, 0))[3] == 0
