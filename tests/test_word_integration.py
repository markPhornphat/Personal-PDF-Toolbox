"""Real Word tests, opt in with PDF_TOOLBOX_WORD_TESTS=1 on Windows."""

import os
from io import BytesIO
from threading import Event

import pytest
from PIL import Image, ImageChops
from pypdf import PdfWriter

from pdf_toolbox.pdf import Cancelled
from pdf_toolbox.word_com import WordAutomation, inspect_word
from pdf_toolbox.word_conversion import digest, generate, pdf_inputs
from pdf_toolbox.word_layout import PlacementSettings

pytestmark = pytest.mark.skipif(
    os.environ.get("PDF_TOOLBOX_WORD_TESTS") != "1",
    reason="Requires opt-in real Microsoft Word Desktop",
)


def fixture_word(path, pages=2, ending="text", header=True):
    with WordAutomation() as word:
        word.doc = word.app.Documents.Add()
        doc = word.doc
        doc.Content.Text = "\x0c".join(f"Original page {index + 1}" for index in range(pages))
        if header:
            doc.Sections.Last.Headers.Item(1).Range.Text = "Company header"
            doc.Sections.Last.Footers.Item(1).Range.Text = "Company footer"
            doc.Sections.Last.Headers.Item(1).Range.ParagraphFormat.Alignment = 0
            doc.Sections.Last.Footers.Item(1).Range.ParagraphFormat.Alignment = 2
        if ending == "table":
            end = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
            doc.Tables.Add(end, 2, 2).Cell(1, 1).Range.Text = "Final table"
        elif ending == "break":
            end = doc.Range(doc.Content.End - 1, doc.Content.End - 1)
            end.InsertBreak(7)
        doc.SaveAs2(str(path), FileFormat=16)


@pytest.mark.parametrize("ending", ["text", "table", "break"])
def test_real_word_append_and_reopen(tmp_path, ending):
    source = tmp_path / "source.docx"
    fixture_word(source, ending=ending)
    before = digest(source)
    info = inspect_word(source)
    assert len(info.preview_bands) == 3
    header, footer = info.preview_bands[0]
    with Image.open(BytesIO(header)) as top, Image.open(BytesIO(footer)) as bottom:
        for band, edge in ((top, "left"), (bottom, "right")):
            rgb = band.convert("RGB")
            ink = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white")).getbbox()
            assert ink is not None
            if edge == "left":
                assert ink[2] < band.width / 2
            else:
                assert ink[0] > band.width / 2
    pdf = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(400, 200)
    writer.add_blank_page(200, 400)
    writer.write(pdf)
    result = generate(pdf_inputs([pdf]), source, tmp_path / "output.docx", PlacementSettings())
    assert result.final_pages == info.pages + 2
    assert digest(source) == before
    assert inspect_word(result.path).pages == info.pages + 2


def test_real_word_cancel(tmp_path):
    source = tmp_path / "source.docx"
    fixture_word(source)
    before = digest(source)
    pdf = tmp_path / "source.pdf"
    writer = PdfWriter()
    writer.add_blank_page(200, 400)
    writer.write(pdf)
    cancel = Event()

    def report(value):
        if value.stage == "Page appended":
            cancel.set()

    with pytest.raises(Cancelled):
        generate(
            pdf_inputs([pdf]), source, tmp_path / "out.docx", PlacementSettings(), cancel, report
        )
    assert not (tmp_path / "out.docx").exists()
    assert digest(source) == before


def test_preview_renders_tab_stops_and_even_page_headers(tmp_path):
    source = tmp_path / "alternating.docx"
    with WordAutomation() as word:
        word.doc = word.app.Documents.Add()
        word.doc.Content.Text = "Page one\x0cPage two"
        section = word.doc.Sections.Last
        section.PageSetup.OddAndEvenPagesHeaderFooter = True
        odd = section.Headers.Item(1).Range
        odd.Text = "Left label\tRight label"
        odd.Style = -1  # Normal style avoids the inherited Header center tab
        odd.ParagraphFormat.Alignment = 0
        odd.ParagraphFormat.TabStops.Add(430, 2)  # right tab within the text area
        even = section.Headers.Item(3).Range
        even.Text = "Even-page heading"
        even.ParagraphFormat.Alignment = 1
        word.doc.SaveAs2(str(source), FileFormat=16)
    before = digest(source)
    info = inspect_word(source)
    first, second, third = info.preview_bands
    assert first[0] == third[0] and first[0] != second[0]
    with Image.open(BytesIO(first[0])) as header:
        rgb = header.convert("RGB")
        ink = ImageChops.difference(rgb, Image.new("RGB", rgb.size, "white"))
        for region in (
            (0, 0, header.width // 3, header.height),
            (header.width * 2 // 3, 0, header.width, header.height),
        ):
            assert ink.crop(region).getbbox() is not None
    assert digest(source) == before
