from PySide6.QtCore import QSettings
from pypdf import PdfWriter

from pdf_toolbox.app import Window
from pdf_toolbox.word_com import WordInfo
from pdf_toolbox.word_layout import Layout
from pdf_toolbox.word_ui import WORD_TOOL


def test_word_navigation_order_preview_and_settings(qtbot, tmp_path):
    prefs = QSettings(str(tmp_path / "prefs.ini"), QSettings.Format.IniFormat)
    window = Window(prefs)
    qtbot.addWidget(window)
    window.show()
    window.select_tool(WORD_TOOL)
    assert window.active_panel() is window.word_panel
    assert window.nav_buttons[WORD_TOOL].property("active")
    panel = window.word_panel
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
        assert "3 additional Word pages" in panel.summary.text()
        panel.sort_files()
        assert [item.path.name for item in panel.inputs()] == ["2.pdf", "10.pdf"]
        panel.info = WordInfo(
            tmp_path / "existing.docx", 1024, 50, Layout(600, 800, 50, 70, 550, 730)
        )
        panel.refresh()
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
        assert "unavailable" in window.word_panel.word_info.text()
    finally:
        qtbot.waitUntil(lambda: not window.jobs.active and not window.thumbs.active)
        window.close_approved = True
        window.close()
