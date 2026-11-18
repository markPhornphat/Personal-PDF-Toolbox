from threading import Event

from PySide6.QtCore import QModelIndex, QSettings, Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QPushButton
from pypdf import PdfWriter

from pdf_toolbox.app import Window
from pdf_toolbox.word_com import WordInfo
from pdf_toolbox.word_conversion import WordProgress, WordResult
from pdf_toolbox.word_layout import Layout
from pdf_toolbox.word_ui import WORD_TOOL, grip_rect


def test_word_navigation_order_preview_and_settings(qtbot, tmp_path):
    prefs = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    window = Window(prefs)
    qtbot.addWidget(window)
    window.show()
    window.select_tool(WORD_TOOL)
    assert window.active_panel() is window.word_panel
    assert window.nav_buttons[WORD_TOOL].property("active")
    panel = window.word_panel
    assert panel.intake.isVisible()
    assert not panel.details.isVisible()
    assert panel.settings().horizontal == panel.settings().vertical == "Center"
    try:
        paths = []
        for filename, count in [("10.pdf", 2), ("2.pdf", 1)]:
            path = tmp_path / filename
            writer = PdfWriter()
            for _ in range(count):
                writer.add_blank_page(120, 180)
            writer.write(path)
            paths.append(path)
        panel.add_files(paths)
        qtbot.waitUntil(lambda: window.busy is None)
        assert [item.path.name for item in panel.inputs()] == ["10.pdf", "2.pdf"]
        assert panel.summary.text() == "Pages to add: 3"
        assert panel.intake.isVisible()
        panel.sort_files()
        assert [item.path.name for item in panel.inputs()] == ["2.pdf", "10.pdf"]
        panel.info = WordInfo(
            tmp_path / "existing.docx", 1024, 50, Layout(600, 800, 50, 70, 550, 730)
        )
        panel.refresh()
        assert panel.details.isVisible()
        assert not panel.intake.isVisible()
        rect = panel.files.visualItemRect(panel.files.item(0))
        panel.files.update_cursor(grip_rect(rect).center())
        assert panel.files.viewport().cursor().shape() == Qt.CursorShape.OpenHandCursor
        panel.files.update_cursor(rect.center())
        assert panel.files.viewport().cursor().shape() == Qt.CursorShape.ArrowCursor
        model = panel.files.model()
        assert model.moveRow(QModelIndex(), 0, QModelIndex(), 2)
        assert [item.path.name for item in panel.inputs()] == ["10.pdf", "2.pdf"]
        assert panel.files.item(1).text().startswith("2.  2.pdf")
        panel.sort_files()
        assert "53" in panel.word_info.text()
        assert panel.generate_button.isEnabled()
        qtbot.waitUntil(lambda: not window.thumbs.active)
        assert not panel.preview.picture.isNull()
        panel.vertical.setCurrentText("Top")
        assert panel.preview.settings.vertical == "Top"
        panel.navigate(1)
        assert "PDF page 1" in panel.page_caption.text()
        panel.files.setCurrentRow(0)
        panel.files.item(0).setSelected(True)
        panel.remove()
        assert len(panel.inputs()) == 1
        panel.clear()
        assert not panel.generate_button.isEnabled()
        assert panel.intake.isVisible()
    finally:
        qtbot.waitUntil(lambda: not window.jobs.active and not window.thumbs.active)
        window.close_approved = True
        window.close()


def test_docx_inspection_failure_clears_previous_selection(qtbot, tmp_path, monkeypatch):
    prefs = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    window = Window(prefs)
    qtbot.addWidget(window)
    window.select_tool(WORD_TOOL)

    def fail(_):
        raise ValueError("Word is unavailable")

    monkeypatch.setattr("pdf_toolbox.word_ui.inspect_word", fail)
    try:
        window.word_panel.select_word([tmp_path / "missing.docx"])
        qtbot.waitUntil(lambda: window.busy is None)
        assert window.word_panel.info is None
        assert not window.word_panel.generate_button.isEnabled()
        box = window.findChild(QMessageBox)
        assert box.isModal()
        assert "unavailable" in box.text()
        assert not box.iconPixmap().isNull()
        box.accept()
    finally:
        qtbot.waitUntil(lambda: not window.jobs.active and not window.thumbs.active)
        window.close_approved = True
        window.close()


def test_word_progress_details_and_result_modal(qtbot, tmp_path, monkeypatch):
    prefs = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    window = Window(prefs)
    qtbot.addWidget(window)
    window.show()
    window.select_tool(WORD_TOOL)
    panel = window.word_panel
    panel.info = WordInfo(tmp_path / "source.docx", 10, 2, Layout(600, 800, 50, 70, 550, 730))
    panel.folder.setText(str(tmp_path))
    panel.filename.setText("result.docx")
    ready = Event()

    def generate(inputs, source, output, settings, cancel, report, *, overwrite):
        report(WordProgress("Validating placement", total=2, processed=1))
        ready.wait(5)
        return WordResult(output, 2, 1, 2, 4, 1.0)

    monkeypatch.setattr("pdf_toolbox.word_ui.generate", generate)
    try:
        panel.start()
        progress = window.processing
        qtbot.waitUntil(lambda: "Validating placement" in progress.details.text())
        assert progress.details.isHidden()
        assert progress.label.text() == "Generating Word document…"
        assert panel.status.text() == ""
        qtbot.mouseClick(progress.toggle_details, Qt.MouseButton.LeftButton)
        assert progress.details.isVisible()
        qtbot.mouseClick(progress.toggle_details, Qt.MouseButton.LeftButton)
        assert progress.details.isHidden()
        ready.set()
        qtbot.waitUntil(lambda: window.processing is None)
        result = next(
            dialog
            for dialog in window.findChildren(QDialog)
            if dialog.windowTitle() == "Word document saved"
        )
        assert result.isVisible() and result.isModal()
        buttons = {button.text(): button for button in result.findChildren(QPushButton)}
        assert set(buttons) == {"Open Word Document", "Open Output Folder", "Start New Conversion"}
        assert all(not button.icon().isNull() for button in buttons.values())
        qtbot.mouseClick(buttons["Start New Conversion"], Qt.MouseButton.LeftButton)
        assert panel.intake.isVisible()
        assert panel.info is None
    finally:
        ready.set()
        qtbot.waitUntil(lambda: window.processing is None and not window.jobs.active)
        window.close_approved = True
        window.close()
