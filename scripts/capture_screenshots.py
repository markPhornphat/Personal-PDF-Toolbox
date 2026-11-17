"""Capture the actual Qt application with synthetic documents."""

import sys
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QSettings, QTemporaryDir, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pdf_toolbox.app import RESOURCE, Window  # noqa: E402
from pdf_toolbox.editor import Object, load_fonts, make_overlay  # noqa: E402
from pdf_toolbox.workspace import TOOLS  # noqa: E402


def wait(app, condition):
    start = monotonic()
    while not condition():
        app.processEvents()
        if monotonic() - start > 12:
            raise TimeoutError("Window did not finish its preview.")


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    assert load_fonts(RESOURCE) >= 0
    output = ROOT / "artifacts" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    scratch = QTemporaryDir()
    assert scratch.isValid()
    window = Window(QSettings(scratch.filePath("settings.ini"), QSettings.Format.IniFormat))
    window.update_timer.stop()
    window.prefs.setValue("auto_updates", False)
    window.prefs.setValue("theme", "Light")
    window.apply_theme()
    window.show()
    app.processEvents()
    assert window.grab().save(str(output / "dashboard.png"))

    source = output / "sample.pdf"
    source.write_bytes(
        make_overlay(
            [
                Object("Text", 30, 29, 270, 35, text="Workshop handout", size=24, bold=True),
                Object(
                    "Text",
                    30,
                    79,
                    260,
                    90,
                    text="Project planning\n\nReview the timeline and discussion notes before the next session.",
                    size=13,
                ),
                Object("Filled rectangle", 30, 170, 265, 2, color="#c4d2e6", fill="#c4d2e6"),
                Object("Text", 30, 198, 238, 40, text="Timeline", size=16, bold=True),
                Object(
                    "Text",
                    30,
                    235,
                    248,
                    130,
                    size=13,
                    text="1. Collect requirements\n\n2. Draft the first milestone\n\n3. Review and share feedback",
                ),
            ],
            330,
            440,
        )
    )
    appendix = output / "appendix.pdf"
    writer = PdfWriter()
    writer.append(source)
    writer.append(source)
    writer.write(appendix)

    window.select_tool(TOOLS[0], [source, appendix])
    wait(app, lambda: not window.busy and not window.workspace.viewer.image.pixmap().isNull())
    window.workspace.thumbnails.fill()
    window.workspace.document_previews.fill()
    wait(app, lambda: not window.thumbs.active)
    window.workspace.thumbnails.fill()
    window.workspace.document_previews.fill()
    app.processEvents()
    assert window.grab().save(str(output / "merge.png"))

    window.select_tool(TOOLS[4], [source])
    wait(app, lambda: not window.busy and not window.editor.loading)
    window.editor.thumbnails.fill()
    wait(app, lambda: not window.thumbs.active)
    window.editor.thumbnails.fill()
    window.editor.add(
        Object("Highlight", 26, 231, 152, 18, fill="#ffd94c", color="#ffd94c", opacity=0.42)
    )
    window.editor.add(Object("Arrow", 181, 238, 37, 27, color="#0968c7"))
    stamp = QImage(95, 36, QImage.Format.Format_ARGB32)
    stamp.fill(QColor("#e6f0fd"))
    window.editor.add(Object("Image", 125, 353, 150, 44, image=stamp))
    window.editor.add(
        Object("Text", 136, 364, 137, 38, text="พร้อมตรวจทาน", size=17, color="#194e82")
    )
    app.processEvents()
    assert window.grab().save(str(output / "editor.png"))
    window.resize(980, 650)
    window.settings.language.setCurrentText("ไทย")
    window.settings.theme.setCurrentText("Dark")
    window.show_panel(window.home)
    app.processEvents()
    assert window.grab().save(str(output / "thai-dark-home.png"))
    window.show_panel(window.settings)
    app.processEvents()
    assert window.grab().save(str(output / "thai-settings.png"))
    window.show_panel(window.editor_view)
    app.processEvents()
    assert window.grab().save(str(output / "thai-dark-editor.png"))
    window.close_approved = True
    window.close()
    for path in (source, appendix):
        path.unlink()


if __name__ == "__main__":
    main()
