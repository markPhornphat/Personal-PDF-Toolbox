from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPointF, QSettings, Qt, QUrl
from PySide6.QtGui import QColor, QDropEvent, QImage
from PySide6.QtWidgets import QApplication
from pypdf import PdfReader, PdfWriter

from pdf_toolbox import app
from pdf_toolbox.editor import Object, load_fonts, make_overlay
from pdf_toolbox.pdf import Page, dimensions, export, render
from pdf_toolbox.workspace import TOOLS


@pytest.fixture(scope="session", autouse=True)
def fonts(qapp):
    assert load_fonts(app.RESOURCE) >= 0


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setattr(
        app,
        "preferences",
        lambda: QSettings(
            str(tmp_path / "settings.ini"),
            QSettings.Format.IniFormat,
        ),
    )
    ui = app.Window()
    ui.show()
    yield ui
    ui.hide()
    QApplication.clipboard().clear()
    ui.close_approved = True
    qtbot.waitUntil(lambda: not ui.jobs.active and not ui.thumbs.active, timeout=10000)
    ui.close()


def make_pdf(path, rotation=0):
    writer = PdfWriter()
    page = writer.add_blank_page(width=240, height=160)
    page.cropbox.lower_left = (20, 12)
    page.cropbox.upper_right = (220, 142)
    page.rotate(rotation)
    writer.add_blank_page(width=130, height=185)
    writer.write(path)
    return path


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_vector_overlay_uses_visible_crop_and_rotation(qapp, tmp_path, rotation):
    path = make_pdf(tmp_path / "rotated.pdf", rotation)
    page = Page(path, 0)
    width, height = dimensions(page, 72)
    shape = Object("Filled rectangle", 15, 23, 26, 17, color="#ff0000", fill="#ff0000")
    overlay = make_overlay([shape], width, height)
    out = tmp_path / "output.pdf"
    export([page], out, overlays={0: overlay})
    result = render(Page(out, 0), dpi=72).convert("RGB")
    assert result.getpixel((24, 29)) == (255, 0, 0)
    assert result.getpixel((72, 29)) == (255, 255, 255)
    assert PdfReader(out).pages[0].rotation == rotation


def test_thai_editor_text_is_rendered_to_vector_pdf(qapp, tmp_path):
    from io import BytesIO

    content = "ภาษาไทย เก้าอี้ English"
    overlay = make_overlay([Object("Text", 10, 10, 180, 100, text=content)], 200, 160)
    reader = PdfReader(BytesIO(overlay))
    assert "English" in reader.pages[0].extract_text()
    assert "/Font" in reader.pages[0]["/Resources"]
    path = tmp_path / "thai-overlay.pdf"
    path.write_bytes(overlay)
    result = render(Page(path, 0), dpi=144).convert("RGB")
    assert result.crop((20, 20, 140, 75)).getextrema()[0][0] < 200


def test_gui_workflows_and_safety(window, qtbot, tmp_path, monkeypatch):
    import socket

    def deny(*args, **kwargs):
        pytest.fail("A PDF operation attempted to use the network.")

    monkeypatch.setattr(socket, "create_connection", deny)
    monkeypatch.setattr(socket.socket, "connect", deny)
    source = make_pdf(tmp_path / "source.pdf")
    original = source.read_bytes()
    first_output = tmp_path / "merged.pdf"
    pending: list[Path] = []
    failures = []

    def result(files, error):
        if error:
            failures.append(error)
        else:
            pending.extend(files)

    monkeypatch.setattr(window, "export_done", result)

    def load_tool(mode, paths):
        window.select_tool(mode)
        window.accept_files(paths)
        qtbot.waitUntil(lambda: window.busy is None, timeout=10000)

    def export_workspace(target):
        previous = len(pending)
        monkeypatch.setattr(window, "destination", lambda *_: target)
        window.workspace.export_button.click()
        qtbot.waitUntil(lambda: len(pending) > previous or bool(failures), timeout=10000)
        assert not failures

    load_tool(TOOLS[0], [source])
    window.workspace.move(1)
    export_workspace(first_output)
    assert [page.mediabox.width for page in PdfReader(first_output).pages] == [130, 240]

    load_tool(TOOLS[1], [source])
    destination = tmp_path / "split"
    destination.mkdir()
    export_workspace(destination)
    assert len(list(destination.glob("*.pdf"))) == 2

    load_tool(TOOLS[2], [source])
    window.workspace.listing.item(0).setSelected(True)
    window.workspace.action.setCurrentText("Extract selected")
    second = tmp_path / "extracted.pdf"
    export_workspace(second)
    assert len(PdfReader(second).pages) == 1

    load_tool(TOOLS[3], [source])
    window.workspace.fmt.setCurrentText("PNG")
    images = tmp_path / "images"
    images.mkdir()
    export_workspace(images)
    assert len(list(images.glob("*.png"))) == 2

    load_tool(TOOLS[4], [source])
    qtbot.waitUntil(lambda: not window.editor.loading, timeout=10000)
    screenshot = QImage(20, 20, QImage.Format.Format_RGB32)
    screenshot.fill(QColor("#22cc33"))
    QApplication.clipboard().setImage(screenshot)
    window.editor.paste(QApplication.clipboard().mimeData(), QPointF(25, 25))
    window.editor.add(Object("Text", 18, 74, 175, 45, text="Thai ภาษาไทย"))
    window.editor.canvas.setFocus()
    qtbot.keyClick(window.editor.canvas, Qt.Key.Key_Right)
    window.editor.copy_objects()
    window.editor.paste(QApplication.clipboard().mimeData())
    assert len(window.editor.items()) == 3
    window.editor.undo()
    assert len(window.editor.items()) == 2
    output = tmp_path / "edited.pdf"
    prior = len(pending)
    monkeypatch.setattr(window, "destination", lambda *_: output)
    window.save_editor()
    qtbot.waitUntil(lambda: len(pending) > prior or bool(failures), timeout=10000)
    assert not failures
    assert not window.editor.dirty
    assert render(Page(output, 0), dpi=72).convert("RGB").getpixel((31, 32)) == (34, 204, 51)
    assert source.read_bytes() == original


def test_drop_and_clipboard_file_references(window, qtbot, tmp_path):
    path = make_pdf(tmp_path / "drop.pdf")
    source = QMimeData()
    source.setUrls([QUrl.fromLocalFile(str(path))])
    window.select_tool(TOOLS[0])
    dropped = QDropEvent(
        QPointF(20, 20),
        Qt.DropAction.CopyAction,
        source,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.workspace.listing.dropEvent(dropped)
    qtbot.waitUntil(lambda: not window.busy)
    assert dropped.isAccepted()
    assert window.workspace.listing.count() == 2
    clipboard = QMimeData()
    clipboard.setUrls([QUrl.fromLocalFile(str(path))])
    QApplication.clipboard().setMimeData(clipboard)
    window.workspace.listing.setFocus()
    window.paste()
    qtbot.waitUntil(lambda: not window.busy)
    assert window.workspace.listing.count() == 4
