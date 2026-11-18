from threading import Event

import pytest
from pypdf import PdfWriter

from pdf_toolbox.pdf import Cancelled
from pdf_toolbox.word_layout import Layout, PlacementSettings, fit_image, natural_key
from pdf_toolbox.word_conversion import generate, pdf_inputs


def test_fit_preserves_ratio_and_safe_area():
    layout = Layout(600, 800, 60, 70, 540, 700)
    for horizontal in ("Left", "Center", "Right"):
        for vertical in ("Top", "Center", "Bottom"):
            rect = fit_image(
                layout,
                1200,
                500,
                PlacementSettings(horizontal=horizontal, vertical=vertical, scale=200),
            )
            assert rect.width / rect.height == pytest.approx(2.4)
            assert rect.x >= layout.left + 5 * 72 / 25.4
            assert rect.right <= layout.right - 5 * 72 / 25.4 + 0.001
            assert rect.bottom <= layout.bottom - 5 * 72 / 25.4 + 0.001


def test_invalid_layout_and_settings():
    with pytest.raises(ValueError):
        fit_image(Layout(600, 800, 50, 500, 550, 510), 100, 100, PlacementSettings())
    with pytest.raises(ValueError):
        PlacementSettings(dpi=72)
    with pytest.raises(ValueError):
        PlacementSettings(scale=float("nan"))


def test_natural_sort():
    assert sorted(["10.pdf", "2.pdf", "1.pdf"], key=natural_key) == ["1.pdf", "2.pdf", "10.pdf"]


def make_pdf(path, count):
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(120, 180)
    writer.write(path)
    return path


def test_intake_order_duplicates_and_corrupt(tmp_path):
    a, b = make_pdf(tmp_path / "2.pdf", 2), make_pdf(tmp_path / "1.pdf", 1)
    inputs = pdf_inputs([a, b])
    assert [item.path for item in inputs] == [a, b]
    assert sum(item.pages for item in inputs) == 3
    with pytest.raises(ValueError, match="Duplicate"):
        pdf_inputs([a, a])
    broken = tmp_path / "bad.pdf"
    broken.write_bytes(b"broken")
    with pytest.raises(ValueError, match="bad.pdf"):
        pdf_inputs([broken])


class FakeWord:
    fail = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def open(self, path):
        self.path = path
        self.count = 0
        return 5

    def layout(self):
        return Layout(600, 800, 50, 60, 550, 740)

    def append(self, image, settings, expected):
        assert image.is_file()
        self.count += 1

    def validate_save(self, expected, count):
        assert expected == 5 + self.count
        if self.fail:
            raise ValueError("validation failed")
        self.path.write_bytes(b"validated")


def test_transaction_validation_and_order(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"original")
    inputs = pdf_inputs([make_pdf(tmp_path / "a.pdf", 2)])
    output = tmp_path / "output.docx"
    result = generate(inputs, source, output, PlacementSettings(), backend=FakeWord)
    assert result.final_pages == 7
    assert source.read_bytes() == b"original"
    assert output.read_bytes() == b"validated"
    assert not list(tmp_path.glob(".word-*"))
    with pytest.raises(FileExistsError):
        generate(inputs, source, output, PlacementSettings(), backend=FakeWord)

    class Failed(FakeWord):
        fail = True

    with pytest.raises(ValueError, match="validation"):
        generate(inputs, source, output, PlacementSettings(), overwrite=True, backend=Failed)
    assert output.read_bytes() == b"validated"


def test_cancel_and_source_alias(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"original")
    inputs = pdf_inputs([make_pdf(tmp_path / "a.pdf", 1)])
    with pytest.raises(ValueError):
        generate(inputs, source, source, PlacementSettings(), backend=FakeWord)
    cancelled = Event()
    cancelled.set()
    output = tmp_path / "out.docx"
    with pytest.raises(Cancelled):
        generate(inputs, source, output, PlacementSettings(), cancelled, backend=FakeWord)
    assert not output.exists()
    assert source.read_bytes() == b"original"


def test_cancel_during_validation_does_not_replace_existing_output(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"original")
    output = tmp_path / "existing.docx"
    output.write_bytes(b"existing output")
    inputs = pdf_inputs([make_pdf(tmp_path / "a.pdf", 1)])
    cancelled = Event()

    class CancelOnValidate(FakeWord):
        def validate_save(self, expected, count):
            super().validate_save(expected, count)
            cancelled.set()

    with pytest.raises(Cancelled):
        generate(
            inputs,
            source,
            output,
            PlacementSettings(),
            cancelled,
            overwrite=True,
            backend=CancelOnValidate,
        )
    assert output.read_bytes() == b"existing output"
    assert source.read_bytes() == b"original"
    assert not list(tmp_path.glob(".word-*"))


def test_changed_destination_is_not_overwritten(tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"original")
    output = tmp_path / "existing.docx"
    output.write_bytes(b"previous output")
    inputs = pdf_inputs([make_pdf(tmp_path / "a.pdf", 1)])

    class ConcurrentEdit(FakeWord):
        def validate_save(self, expected, count):
            super().validate_save(expected, count)
            output.write_bytes(b"edited while processing")

    with pytest.raises(FileExistsError, match="changed during processing"):
        generate(
            inputs, source, output, PlacementSettings(), overwrite=True, backend=ConcurrentEdit
        )
    assert output.read_bytes() == b"edited while processing"
