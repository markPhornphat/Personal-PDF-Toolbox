from contextlib import closing
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPointF, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDropEvent, QImage
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QWidget,
)
from pypdf import PdfReader, PdfWriter

from pdf_toolbox import app
from pdf_toolbox.editor import Object, load_fonts, make_overlay
from pdf_toolbox.pdf import (
    Cancelled,
    Page,
    check_cancelled,
    dimensions,
    export,
    locked_page,
    render,
)
from pdf_toolbox.workspace import ORGANIZE, TOOLS


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


def test_home_mascot_search_and_navigation(window):
    assert window.findChild(QWidget, "Mascot").isVisible()
    assert not window.drop.mascot.pixmap.isNull()
    window.search.setText("no matching tool")
    assert window.findChild(QLabel, "NoToolResults").isVisible()
    window.search.setText("split")
    assert [card for card in window.cards if card.isVisible()] == [window.cards[1]]
    window.cards[1].click()
    assert window.workspace.mode == TOOLS[1]
    assert window.nav_buttons[TOOLS[1]].property("active") is True
    assert window.nav_buttons["Home"].property("active") is False
    window.nav_buttons["Home"].click()
    assert window.findChild(QWidget, "Mascot").isVisible()


def test_sidebar_after_loading_images(window, qtbot, tmp_path):
    source = make_pdf(tmp_path / "conversion.pdf")
    window.select_tool(TOOLS[3], [source])
    qtbot.waitUntil(lambda: window.busy is None)
    for tool in (*TOOLS[:3], TOOLS[4], TOOLS[3]):
        button = window.nav_buttons[tool]
        assert not button.icon().isNull()
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
        assert button.property("active") is True


def test_empty_tools_have_localized_file_intake(window, qtbot, tmp_path, monkeypatch):
    source = make_pdf(tmp_path / "intake.pdf")
    for tool in TOOLS:
        window.nav_buttons[tool].click()
        assert window.stack.currentWidget() is window.empty_tool
        assert window.empty_tool.title.text() == tool
        assert window.empty_tool.description.text()
        assert not window.empty_tool.icon.pixmap().isNull()
        assert window.empty_tool.drop.acceptDrops()
        assert window.empty_tool.choose.toolTip()
        expected = (
            "Drop a PDF here" if tool in {TOOLS[1], TOOLS[4]} else "Drop one or more PDFs here"
        )
        assert window.empty_tool.hint.text() == expected

    window.nav_buttons[TOOLS[4]].click()
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(source), ""))
    qtbot.mouseClick(window.empty_tool.choose, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.stack.currentWidget() is window.editor_view)
    assert len(window.editor.references) == 2

    window.nav_buttons[TOOLS[2]].click()
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(source))])
    event = QDropEvent(
        QPointF(10, 10),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.empty_tool.drop.dropEvent(event)
    qtbot.waitUntil(lambda: window.stack.currentWidget() is window.workspace)
    assert event.isAccepted()
    window.workspace.listing.selectAll()
    window.workspace.remove()
    assert window.stack.currentWidget() is window.empty_tool
    assert window.empty_tool.title.text() == TOOLS[2]


def test_organize_exports_independent_rotations_blank_and_reversed_order(
    window, qtbot, tmp_path, monkeypatch
):
    source = make_pdf(tmp_path / "organize.pdf", rotation=90)
    second = make_pdf(tmp_path / "insert.pdf")
    originals = {path: path.read_bytes() for path in (source, second)}
    result = tmp_path / "organized.pdf"
    outputs = []
    monkeypatch.setattr(window, "destination", lambda *_: result)
    monkeypatch.setattr(window, "export_done", lambda files, error: outputs.append((files, error)))
    window.nav_buttons[ORGANIZE].click()
    assert window.empty_tool.title.text() == ORGANIZE
    assert window.empty_tool.choose.cursor().shape() == Qt.CursorShape.PointingHandCursor
    window.accept_files([source])
    workspace = window.workspace
    qtbot.waitUntil(lambda: workspace.listing.count() == 2)

    def click_action(name):
        button = next(
            item
            for item in workspace.findChildren(QPushButton)
            if name in {item.text(), item.accessibleName()}
        )
        assert button.isVisible()
        assert button.cursor().shape() == Qt.CursorShape.PointingHandCursor
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)

    workspace.listing.item(0).setSelected(True)
    click_action("Duplicate")
    workspace.listing.setCurrentRow(1)
    click_action("Rotate right")
    assert [page.rotation for page in workspace.pages()] == [0, 90, 0]
    click_action("Blank page")
    assert workspace.listing.item(2).text() == "Blank page\nA4"
    qtbot.waitUntil(lambda: workspace.viewer.image.pixmap().width() > 0)
    assert render(workspace.pages()[2], dpi=72).size == (595, 842)

    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(second), ""))
    monkeypatch.setattr(app, "ask_text", lambda *_: ("2", True))
    click_action("Add a page range…")
    qtbot.waitUntil(lambda: workspace.listing.count() == 5)
    forward = workspace.pages()
    click_action("Reverse order")
    assert workspace.pages() == forward[::-1]
    click_action("Undo")
    assert workspace.pages() == forward
    click_action("Redo")
    click_action("Export…")
    qtbot.waitUntil(lambda: bool(outputs))
    assert outputs == [([result], None)]
    pages = PdfReader(result).pages
    assert [(int(page.mediabox.width), page.rotation) for page in pages] == [
        (130, 0),
        (130, 0),
        (595, 0),
        (240, 180),
        (240, 90),
    ]
    for index, reference in enumerate(workspace.pages()):
        assert render(reference, dpi=72).size == render(Page(result, index), dpi=72).size
    assert all(path.read_bytes() == data for path, data in originals.items())


def test_sidebar_theme_and_button_hover_follow_settings(window):
    assert window.theme_button.toolTip() == "Choose the app appearance."
    window.theme_actions["Dark"].trigger()
    assert window.settings.theme.currentData() == "Dark"
    assert window.prefs.value("theme") == "Dark"
    assert window.theme_actions["Dark"].isChecked()
    window.settings.theme.setCurrentText("Light")
    assert window.theme_actions["Light"].isChecked()
    window.settings.language.setCurrentText("ไทย")
    assert window.theme_button.toolTip() == "เลือกรูปแบบสีของแอป"
    assert window.theme_actions["Dark"].toolTip() == "ใช้ธีมมืด"
    for button in [*window.nav_buttons.values(), window.workspace.export_button]:
        assert button.toolTip()


def test_theme_icon_is_centered_and_opens_theme_menu(window, qtbot):
    window.settings.theme.setCurrentText("Dark")
    button = window.theme_button
    screenshot = button.grab()
    picture = screenshot.toImage()
    ink = QColor(window.theme_palette["primary"])
    columns = [
        x
        for x in range(picture.width())
        if any(picture.pixelColor(x, y) == ink for y in range(picture.height()))
    ]
    assert columns
    assert (
        abs(columns[0] + columns[-1] - (picture.width() - 1)) <= 4 * screenshot.devicePixelRatio()
    )
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    menu = QApplication.activePopupWidget()
    assert isinstance(menu, QMenu)
    assert window.theme_actions["Dark"].isChecked()
    qtbot.keyClick(menu, Qt.Key.Key_Escape)


def test_about_dialog_shows_mascot_and_checks_for_updates(window, qtbot, monkeypatch):
    checks = []
    monkeypatch.setattr(window, "check_updates", lambda *, manual: checks.append(manual))
    qtbot.mouseClick(window.nav_buttons["About"], Qt.MouseButton.LeftButton)
    dialog = QApplication.activeModalWidget()
    assert isinstance(dialog, QDialog)
    assert dialog.objectName() == "AboutDialog"
    assert dialog.findChild(QWidget, "Mascot").isVisible()
    assert dialog.findChild(QLabel, "AboutVersion").text() == f"Version {app.VERSION}"
    actions = {button.text(): button for button in dialog.findChildren(QPushButton)}
    assert set(actions) == {"Check for updates", "User guide", "Licenses", "Close"}
    assert all(button.toolTip() for button in actions.values())
    qtbot.mouseClick(actions["Check for updates"], Qt.MouseButton.LeftButton)
    assert checks == [True]
    assert QApplication.activeModalWidget() is dialog
    dialog.reject()


def test_home_file_paste_from_search(window, qtbot, tmp_path):
    source = make_pdf(tmp_path / "pasted.pdf")
    clipboard = QMimeData()
    clipboard.setUrls([QUrl.fromLocalFile(str(source))])
    QApplication.clipboard().setMimeData(clipboard)
    window.search.setFocus()
    qtbot.keyClick(window.search, Qt.Key.Key_V, Qt.KeyboardModifier.ControlModifier)
    menu = QApplication.activePopupWidget()
    assert isinstance(menu, QMenu)
    action = menu.actions()[0]
    assert not action.icon().isNull()
    qtbot.mouseClick(menu, Qt.MouseButton.LeftButton, pos=menu.actionGeometry(action).center())
    qtbot.waitUntil(lambda: window.workspace.listing.count() == 2)
    assert window.nav_buttons[TOOLS[0]].property("active") is True
    assert QApplication.activePopupWidget() is None


def test_page_captions_stay_visible_when_thumbnails_arrive(window, qtbot, tmp_path):
    source = make_pdf(tmp_path / "source.pdf")
    window.select_tool(TOOLS[2], [source])
    listing = window.workspace.listing
    qtbot.waitUntil(lambda: listing.count() == 2)
    item = listing.item(0)
    assert item.text().splitlines() == ["source.pdf", "Page 1"]
    rect = listing.visualItemRect(item)
    assert listing.viewport().rect().contains(rect)
    caption = rect.adjusted(5, rect.height() - 50, -5, -4)
    before = listing.viewport().grab(caption).toImage()
    title = item.text()
    item.setText("\n")
    assert listing.viewport().grab(caption).toImage() != before
    item.setText(title)
    qtbot.waitUntil(lambda: not item.icon().isNull(), timeout=3000)
    assert listing.visualItemRect(item) == rect
    assert listing.viewport().grab(caption).toImage() == before
    changes = []
    listing.model().dataChanged.connect(lambda *_: changes.append(True))
    window.workspace.thumbnails.fill()
    assert not changes


def test_processing_modal_animates_reports_and_cancels(window, qtbot):
    results = []

    def work(cancelled, progress):
        progress(2, 4)
        cancelled.wait(timeout=5)
        check_cancelled(cancelled)

    window.run_job(work, "Exporting PDF pages…", lambda value, error: results.append(error))
    dialog = window.processing
    assert dialog.isVisible()
    assert dialog.isModal()
    assert dialog.dog.animation.isActive()
    assert not dialog.dog.picture.isNull()
    qtbot.waitUntil(lambda: dialog.percent.text() == "50%")
    assert dialog.bar.value() == 2
    assert dialog.dog.fraction == 0.5
    pose = dialog.dog.grab().toImage()
    qtbot.waitUntil(lambda: dialog.dog.grab().toImage() != pose)
    qtbot.mouseClick(dialog.cancel, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window.processing is None)
    assert len(results) == 1 and isinstance(results[0], Cancelled)
    qtbot.mouseClick(window.nav_buttons[TOOLS[1]], Qt.MouseButton.LeftButton)
    assert window.workspace.mode == TOOLS[1]


def test_thai_language_switch_preserves_operation_and_page_selection(window, qtbot, tmp_path):
    source = make_pdf(tmp_path / "คู่มือ.pdf")
    window.select_tool(TOOLS[1], [source])
    qtbot.waitUntil(lambda: not window.busy)
    window.workspace.groups.setCurrentText("Every N pages")
    window.workspace.range.setText("2")
    window.workspace.listing.setCurrentRow(1)
    before = window.workspace.output_plan()
    window.settings.language.setCurrentText("ไทย")
    assert window.workspace.groups.currentText() == "แบ่งทุก N หน้า"
    assert window.workspace.output_plan() == before
    assert window.workspace.listing.currentRow() == 1
    assert window.workspace.viewer.counter.text() == "หน้า 2 จาก 2"
    assert "ส่งออก…" in {button.text() for button in window.findChildren(QPushButton)}
    assert "โฟลเดอร์ส่งออกเริ่มต้น" in {label.text() for label in window.findChildren(QLabel)}
    assert "ตรวจสอบอัปเดตจาก GitHub ในเบื้องหลัง" in {
        box.text() for box in window.findChildren(QCheckBox)
    }
    window.settings.language.setCurrentText("English")
    assert window.workspace.groups.currentText() == "Every N pages"
    assert window.workspace.output_plan() == before


def test_thai_clipboard_text_exports_with_combining_marks(window, qtbot, tmp_path, monkeypatch):
    path = make_pdf(tmp_path / "ต้นฉบับ.pdf")
    window.settings.language.setCurrentText("ไทย")
    window.select_tool(TOOLS[4], [path])
    qtbot.waitUntil(lambda: not window.busy and not window.editor.loading)
    text = "เก้าอี้ น้ำผึ้ง กุ้ง"
    QApplication.clipboard().setText(text)
    window.editor.paste(QApplication.clipboard().mimeData(), QPointF(12, 20))
    assert window.editor.items()[0].obj.text == text
    output = tmp_path / "แก้ไขแล้ว.pdf"
    results = []
    monkeypatch.setattr(window, "destination", lambda *_: output)
    monkeypatch.setattr(window, "export_done", lambda *args: results.append(args))
    window.save_editor()
    qtbot.waitUntil(lambda: bool(results))
    assert results == [([output], None)]
    assert PdfReader(output).pdf_header >= "%PDF-1.4"
    with locked_page(Page(output, 0)) as page:
        with closing(page.get_textpage()) as textpage:
            assert text in textpage.get_text_range()
    assert render(Page(output, 0), dpi=144).crop((24, 40, 280, 110)).getextrema()[0][0] < 100


def test_thai_replacement_text_excludes_clipped_lines(qapp, tmp_path):
    obj = Object("Text", 8, 12, 90, 20, text="PDF เก้าอี้\nข้อความที่ซ่อน")
    output = tmp_path / "clipped.pdf"
    output.write_bytes(make_overlay([obj], 200, 160))
    with locked_page(Page(output, 0)) as page, closing(page.get_textpage()) as textpage:
        assert "ข้อความที่ซ่อน" not in textpage.get_text_range()


def test_thai_confirmation_translates_buttons_and_preserves_choice(window):
    window.settings.language.setCurrentText("ไทย")
    seen = []

    def decline():
        box = window.findChild(QMessageBox)
        no = box.button(QMessageBox.StandardButton.No)
        seen.extend([box.windowTitle(), box.text(), no.text()])
        no.click()

    QTimer.singleShot(0, decline)
    assert not window.confirm("Reset preferences?", "This restores the default app preferences.")
    assert seen == [
        "คืนค่าการตั้งค่าเริ่มต้นหรือไม่",
        "การตั้งค่าแอปจะกลับเป็นค่าเริ่มต้น",
        "ไม่",
    ]


def test_update_checks_consent_and_rejects_tampering_before_launch(window, tmp_path, monkeypatch):
    import hashlib
    import json

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    from pdf_toolbox.updater import ASSET, Config, Release, verify_manifest, version_tuple

    major, minor, patch = version_tuple(app.VERSION)
    version = f"{major}.{minor}.{patch + 1}"
    key = Ed25519PrivateKey.generate()
    config = Config("test-owner/test-private-releases", key.public_key().public_bytes_raw(), True)
    content = b"installer from a signed test release"
    installer = tmp_path / ASSET
    installer.write_bytes(content)
    payload = json.dumps(
        {
            "schema_version": 1,
            "app_id": "pdf-toolbox",
            "version": version,
            "tag": f"v{version}",
            "repository": config.repository,
            "platform": "win32",
            "architecture": "x64",
            "installer_filename": ASSET,
            "installer_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "release_date": "2026-11-17",
        }
    ).encode()
    window.update_config = config
    window.release = Release(
        verify_manifest(config, payload, key.sign(payload), f"v{version}", app.VERSION), 3, ""
    )
    window.installer = installer
    window.update_button.show()
    window.settings.language.setCurrentText("ไทย")
    launched = []
    alerts = []
    monkeypatch.setattr(app.subprocess, "Popen", lambda args: launched.append(args))
    monkeypatch.setattr(window, "alert", alerts.append)
    window.offer_update()
    assert window.update_notice.isVisible()
    window.update_notice.later.click()
    assert not launched
    assert not window.prefs.contains("pending_upgrade")

    monkeypatch.setattr(app, "PACKAGED", True)
    installer.write_bytes(b"!" * len(content))
    window.install_update()
    assert alerts
    assert not launched
    assert window.installer is None
    assert window.update_button.text() == "มีอัปเดต"
    assert not window.prefs.contains("pending_upgrade")

    installer.write_bytes(content)
    window.installer = installer
    window.install_update()
    assert launched[0][0] == str(installer)
    assert "/VERYSILENT" in launched[0]
    assert "/AUTORESTART=1" in launched[0]
    assert "/LANG=thai" in launched[0]
    persisted = QSettings(window.prefs.fileName(), QSettings.Format.IniFormat)
    assert persisted.value("pending_upgrade") == version
    assert persisted.value("language") == "ไทย"


def test_startup_updates_check_once_per_day_or_boot(window, qtbot, monkeypatch):
    from types import SimpleNamespace

    from pdf_toolbox.updater import Config

    window.update_config = Config("owner/repo", bytes(32), False)
    window.update_timer.stop()
    window.prefs.setValue("auto_updates", True)
    calls = []
    monkeypatch.setattr(
        window,
        "client",
        lambda: SimpleNamespace(check=lambda version: calls.append(version)),
    )
    window.startup_update_key = "2026-11-18/boot-a"
    window.check_updates(manual=False)
    qtbot.waitUntil(lambda: window.update_running is None)
    assert len(calls) == 1
    window.check_updates(manual=False)
    assert window.update_running is None and len(calls) == 1
    for key in ("2026-11-19/boot-a", "2026-11-19/boot-b"):
        window.startup_update_key = key
        window.check_updates(manual=False)
        qtbot.waitUntil(lambda: window.update_running is None)
    assert len(calls) == 3
    window.check_updates(manual=True)
    qtbot.waitUntil(lambda: window.update_running is None)
    assert len(calls) == 4
    assert window.settings.check.isEnabled()


def test_about_check_shows_loading_and_current_status(window, qtbot, monkeypatch):
    from threading import Event
    from types import SimpleNamespace

    from pdf_toolbox.updater import Config

    finished = Event()
    window.update_config = Config("owner/repo", bytes(32), False)
    monkeypatch.setattr(
        window,
        "client",
        lambda: SimpleNamespace(check=lambda _: (finished.wait(3), None)[1]),
    )
    window.about()
    window.about_check.click()
    assert window.about_check.text() == "Checking for updates…"
    assert not window.about_check.isEnabled()
    finished.set()
    qtbot.waitUntil(lambda: window.update_running is None)
    assert window.about_check.isEnabled()
    assert window.about_status.text() == "This version is current."
    window.about_dialog.reject()


def test_update_now_downloads_and_launches_without_second_click(
    window, qtbot, tmp_path, monkeypatch
):
    from types import SimpleNamespace

    source = tmp_path / "PDF-Toolbox-Setup-x64.exe"
    source.write_bytes(b"simulated verified installer")
    window.release = SimpleNamespace(manifest=SimpleNamespace(version="0.2.2"))
    downloads = []
    launches = []
    monkeypatch.setattr(app, "PACKAGED", True)
    monkeypatch.setattr(app, "verify_file", lambda *args: None)
    monkeypatch.setattr(app.subprocess, "Popen", lambda args: launches.append(args))
    monkeypatch.setattr(window, "confirm", lambda *_: pytest.fail("Unexpected second confirmation"))

    def download(release, directory, cancel, progress):
        downloads.append(release)
        progress(5, 10)
        return source

    monkeypatch.setattr(window, "client", lambda: SimpleNamespace(download=download))
    window.offer_update()
    window.update_notice.update.click()
    assert window.update_dialog is not None
    qtbot.waitUntil(lambda: bool(launches))
    assert len(downloads) == len(launches) == 1
    assert "/VERYSILENT" in launches[0]
    assert "/AUTORESTART=1" in launches[0]
    assert window.prefs.value("pending_upgrade") == "0.2.2"


def test_update_now_waits_for_unsaved_changes(window, monkeypatch):
    from types import SimpleNamespace

    window.release = SimpleNamespace(manifest=SimpleNamespace(version="0.2.2"))
    window.editor.objects = {0: [Object("Text", 1, 1, 50, 20, text="Pending edits")]}
    downloads = []
    monkeypatch.setattr(window, "download_update", lambda: downloads.append(True))
    monkeypatch.setattr(window, "question", lambda *_: QMessageBox.StandardButton.Cancel)
    window.start_update()
    assert not downloads
    assert window.editor.dirty
