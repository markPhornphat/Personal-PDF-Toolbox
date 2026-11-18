"""Capture the Word panel using synthetic local PDF/Word documents."""

import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTemporaryDir
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from capture_screenshots import wait  # noqa: E402
from pdf_toolbox.app import RESOURCE, Window  # noqa: E402
from pdf_toolbox.editor import Object, load_fonts, make_overlay  # noqa: E402
from pdf_toolbox.word_com import WordAutomation  # noqa: E402
from pdf_toolbox.word_ui import WORD_TOOL  # noqa: E402


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    load_fonts(RESOURCE)
    output = ROOT / "artifacts" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    scratch = QTemporaryDir()
    assert scratch.isValid()
    root = Path(scratch.path())
    pdf = root / "Workshop handout.pdf"
    pdf.write_bytes(
        make_overlay(
            [
                Object("Text", 30, 35, 265, 40, text="Workshop notes", size=24, bold=True),
                Object(
                    "Text",
                    30,
                    95,
                    265,
                    180,
                    size=14,
                    text="1. Review the project timeline\n\n2. Agree on next steps\n\n3. Share meeting notes",
                ),
            ],
            330,
            440,
        )
    )
    docx = root / "Meeting notes.docx"
    with WordAutomation() as word:
        word.doc = word.app.Documents.Add()
        word.doc.Content.Text = "Original meeting notes"
        word.doc.Sections.Last.Headers.Item(1).Range.Text = "Workshop / Planning team"
        word.doc.Sections.Last.Footers.Item(1).Range.Text = "Internal working notes"
        word.doc.SaveAs2(str(docx), FileFormat=16)
    window = Window(QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat))
    window.update_timer.stop()
    window.prefs.setValue("theme", "Light")
    window.apply_theme()
    window.resize(1260, 1000)
    window.show()
    window.select_tool(WORD_TOOL, [pdf])
    wait(app, lambda: not window.busy)
    window.word_panel.select_word([docx])
    wait(app, lambda: not window.busy and not window.thumbs.active)
    app.processEvents()
    assert window.word_panel.info is not None
    assert window.grab().save(str(output / "pdf-to-word.png"))
    window.close_approved = True
    window.close()
    print(output / "pdf-to-word.png")


if __name__ == "__main__":
    main()
