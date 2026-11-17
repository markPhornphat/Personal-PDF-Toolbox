from __future__ import annotations

import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .editor import Editor, load_fonts
from .jobs import Jobs, message_for
from .pdf import (
    Cancelled,
    Page,
    PasswordRequired,
    check_cancelled,
    export,
    inspect,
    page_range,
    safe_local,
)
from .localization import ask_text, localize_buttons, retranslate_controls, thai_enabled, tr
from .settings import COMMON, DARK, LIGHT, Settings, data_path, preferences
from .updater import Config, Credentials, GitHub, UpdateError, verify_file
from .viewer import local_paths
from .workspace import TOOLS, Workspace

RESOURCE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
PACKAGED = bool(getattr(sys, "frozen", False))
VERSION = (
    (RESOURCE / "VERSION").read_text(encoding="utf-8").strip()
    if PACKAGED
    else tomllib.loads((RESOURCE / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
)
DESCRIPTIONS = (
    "Combine documents and arrange pages",
    "Divide a document into separate files",
    "Keep, remove or extract selected pages",
    "Export pages at the resolution you choose",
    "Add text, pictures and shapes",
)
IMAGE_TYPES = {".png", ".jpg", ".jpeg"}


class DropArea(QFrame):
    files = Signal(list)

    def __init__(self, browse):
        super().__init__()
        self.setObjectName("DropArea")
        self.setAcceptDrops(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 22, 18, 22)
        headline = QLabel("Drop PDF, JPG or PNG files here")
        headline.setObjectName("Section")
        headline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip = QLabel("Select files, or paste copied files with Ctrl+V.")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        choose = QPushButton("Browse files…")
        choose.setProperty("primary", True)
        choose.clicked.connect(browse)
        layout.addWidget(headline)
        layout.addWidget(tip)
        layout.addWidget(choose, alignment=Qt.AlignmentFlag.AlignHCenter)

    def highlight(self, value):
        self.setProperty("dragging", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.highlight(False)
        self.files.emit(local_paths(event.mimeData()))
        event.acceptProposedAction()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"PDF Toolbox {VERSION}")
        self.resize(1260, 790)
        self.setMinimumSize(980, 650)
        self.setAcceptDrops(True)
        self.prefs = preferences()
        self.jobs = Jobs(self)
        self.thumbs = Jobs(self, threads=1)
        self.update_jobs = Jobs(self, threads=1)
        self.busy = None
        self.update_running = None
        self.release = None
        self.installer = None
        self.close_approved = False
        self.translation = {}
        self.update_config = self.load_config()

        self.stack = QStackedWidget()
        self.home = self.build_home()
        self.workspace = Workspace(self.jobs, self.thumbs)
        self.editor = Editor(self.jobs, self.thumbs)
        self.editor_view = self.build_editor()
        self.settings = Settings(self)
        for panel in [self.home, self.workspace, self.editor_view, self.settings]:
            self.stack.addWidget(panel)
        self.workspace.browse.connect(self.browse)
        self.workspace.browse_range.connect(self.browse_range)
        self.workspace.add_files.connect(self.accept_files)
        self.workspace.failed.connect(self.alert)
        self.workspace.run_requested.connect(self.run_workspace)
        self.editor.alert.connect(self.alert)
        self.editor.open_requested.connect(self.accept_files)
        self.editor.changed.connect(self.editor_status)

        main = QWidget()
        columns = QHBoxLayout(main)
        columns.setContentsMargins(14, 12, 14, 12)
        nav = QVBoxLayout()
        brand = QLabel("PDF Toolbox")
        brand.setObjectName("Brand")
        nav.addWidget(brand)
        self.version_label = QLabel()
        nav.addWidget(self.version_label)
        nav.addSpacing(18)
        for label, action in [
            ("Home", lambda: self.show_panel(self.home)),
            *[(tool, lambda name=tool: self.select_tool(name)) for tool in TOOLS],
            ("Settings", lambda: self.show_panel(self.settings)),
            ("About", self.about),
        ]:
            button = QPushButton(label)
            button.setMinimumWidth(145)
            button.clicked.connect(action)
            nav.addWidget(button)
        nav.addStretch()
        self.update_button = QPushButton("Update available")
        self.update_button.clicked.connect(self.offer_update)
        self.update_button.hide()
        nav.addWidget(self.update_button)
        columns.addLayout(nav)
        columns.addWidget(self.stack, 1)
        self.setCentralWidget(main)

        self.progress = QProgressBar()
        self.progress.setMaximumWidth(180)
        self.progress.hide()
        self.cancel = QPushButton("Cancel")
        self.cancel.clicked.connect(self.cancel_work)
        self.cancel.hide()
        self.statusBar().addPermanentWidget(self.progress)
        self.statusBar().addPermanentWidget(self.cancel)
        self.statusBar().addPermanentWidget(QLabel("Documents are processed locally"))
        self.install_shortcuts()
        self.apply_theme()
        self.translate()
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(15 * 60 * 1000)
        self.update_timer.timeout.connect(lambda: self.check_updates(manual=False))
        self.update_timer.start()
        QTimer.singleShot(2000, self, lambda: self.check_updates(manual=False))
        QTimer.singleShot(0, self, self.confirm_upgrade)

    def build_home(self):
        home = QWidget()
        layout = QVBoxLayout(home)
        layout.setContentsMargins(16, 10, 16, 12)
        heading = QLabel("Home")
        heading.setObjectName("Heading")
        layout.addWidget(heading)
        drop = DropArea(self.browse)
        drop.files.connect(self.accept_files)
        layout.addWidget(drop)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search tools")
        self.search.textChanged.connect(self.filter_tools)
        layout.addWidget(self.search)
        label = QLabel("All tools")
        label.setObjectName("Section")
        layout.addWidget(label)
        grid = QGridLayout()
        self.cards = []
        for index, (name, detail) in enumerate(zip(TOOLS, DESCRIPTIONS, strict=True)):
            button = QPushButton(f"{name}\n{detail}")
            button.setObjectName("ToolCard")
            button.setToolTip(detail)
            button.clicked.connect(lambda _, tool=name: self.select_tool(tool))
            grid.addWidget(button, index // 2, index % 2)
            self.cards.append(button)
        layout.addLayout(grid)
        layout.addStretch()
        return home

    def build_editor(self):
        wrap = QWidget()
        panel = QVBoxLayout(wrap)
        buttons = QHBoxLayout()
        title = QLabel("Edit PDF")
        title.setObjectName("Heading")
        buttons.addWidget(title)
        self.editor_label = QLabel()
        buttons.addWidget(self.editor_label)
        buttons.addStretch()
        for label, slot in [
            ("Browse files…", self.browse),
            ("Save", self.save_editor),
            ("Save as…", self.save_editor),
        ]:
            button = QPushButton(label)
            button.clicked.connect(slot)
            if label == "Save as…":
                button.setProperty("primary", True)
            buttons.addWidget(button)
        panel.addLayout(buttons)
        panel.addWidget(self.editor)
        return wrap

    def install_shortcuts(self):
        for sequence, slot in [
            ("Ctrl+O", self.browse),
            ("Ctrl+V", self.paste),
            ("Ctrl+S", self.save_current),
            ("Ctrl+Shift+S", self.save_current),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(slot)

    def load_config(self):
        path = RESOURCE / "update-config.json"
        if not path.is_file():
            return None
        try:
            return Config.load(path)
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def apply_theme(self):
        system = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        theme = self.prefs.value("theme", "System")
        self.setStyleSheet(
            COMMON + (DARK if theme == "Dark" or (theme == "System" and system) else LIGHT)
        )

    def translate(self):
        retranslate_controls(self)
        self.filter_tools(self.search.text())
        self.version_label.setText(tr(self, "Version {version}", version=VERSION))
        self.update_button.setText(
            tr(self, "Ready to install" if self.installer else "Update available")
        )
        self.settings.status.setText(
            tr(self, self.prefs.value("update_status", "No update checks yet"))
        )
        self.workspace.retranslate()
        self.editor.retranslate()
        self.editor_status()

    def filter_tools(self, query):
        for button in self.cards:
            button.setVisible(query.casefold().strip() in button.text().casefold())

    def show_panel(self, panel):
        if not self.busy:
            self.stack.setCurrentWidget(panel)

    def select_tool(self, tool, files=None):
        if self.busy:
            self.notice("Wait for the current PDF operation to finish.")
            return
        if tool == TOOLS[4]:
            self.show_panel(self.editor_view)
        else:
            if self.workspace.mode != tool:
                self.workspace.configure(tool)
            self.workspace.dpi.setValue(self.prefs.value("dpi", 200, type=int))
            self.workspace.quality.setValue(self.prefs.value("quality", 90, type=int))
            self.show_panel(self.workspace)
        self.translate()
        if files:
            self.accept_files(files)

    def browse(self):
        home = self.stack.currentWidget() == self.home
        kind = "PDF and images (*.pdf *.jpg *.jpeg *.png)" if home else "PDF files (*.pdf)"
        names, _ = QFileDialog.getOpenFileNames(self, tr(self, "Choose files"), "", tr(self, kind))
        if names:
            self.accept_files([Path(name) for name in names])

    def paste(self):
        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            focused.paste()
            return
        data = QApplication.clipboard().mimeData()
        if data is None:
            return
        if self.stack.currentWidget() == self.editor_view:
            self.editor.paste(data)
        else:
            self.accept_files(local_paths(data))

    def browse_range(self):
        selected, _ = QFileDialog.getOpenFileName(
            self, tr(self, "Choose a PDF for page insertion"), "", tr(self, "PDF files (*.pdf)")
        )
        if selected:
            self.load_files([Path(selected)], self.workspace, choose_range=True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.accept_files(local_paths(event.mimeData()))
        event.acceptProposedAction()

    def accept_files(self, files):
        if self.busy:
            return
        paths = [path for path in dict.fromkeys(files) if safe_local(path)]
        pdfs = [path for path in paths if path.suffix.lower() == ".pdf"]
        images = [path for path in paths if path.suffix.lower() in IMAGE_TYPES]
        current = self.stack.currentWidget()
        if current == self.home and (pdfs or images):
            self.suggest(pdfs, images)
            return
        if current == self.editor_view and images and not pdfs:
            from PySide6.QtCore import QPointF
            from PySide6.QtGui import QImage

            for path in images:
                self.editor.add_image(QImage(str(path)), QPointF(24, 24))
            return
        if not pdfs:
            self.alert("Choose a local PDF file.")
            return
        if current not in {self.workspace, self.editor_view}:
            self.select_tool(TOOLS[0], pdfs)
            return
        single = current == self.editor_view or self.workspace.mode == TOOLS[1]
        if single and len(pdfs) != 1:
            self.alert("Choose one PDF for this tool.")
            return
        if current == self.editor_view and self.editor.dirty:
            self.resolve_editor(lambda: self.load_files(pdfs, current))
            return
        self.load_files(pdfs, current)

    def suggest(self, pdfs, images):
        if not pdfs:
            self.select_tool(TOOLS[4])
            selected, _ = QFileDialog.getOpenFileName(
                self, tr(self, "Open a PDF for image insertion"), "", tr(self, "PDF files (*.pdf)")
            )
            if selected:
                self.resolve_editor(
                    lambda: self.load_files([Path(selected)], self.editor_view, images=images)
                )
            return
        menu = QMenu(self)
        choices = (TOOLS[0], TOOLS[3]) if len(pdfs) > 1 else TOOLS
        for choice in choices:
            menu.addAction(
                tr(self, choice), lambda tool=choice: self.open_suggestion(tool, pdfs, images)
            )
        menu.exec(self.stack.mapToGlobal(self.stack.rect().center()))

    def open_suggestion(self, tool, pdfs, images):
        self.select_tool(tool)
        if tool == TOOLS[4] and images:
            self.resolve_editor(lambda: self.load_files(pdfs, self.editor_view, images=images))
        else:
            self.accept_files(pdfs)

    def load_files(self, files, panel, images=(), choose_range=False):
        if not all(safe_local(path) for path in files):
            self.alert("Choose files on this computer.")
            return
        ordered = []
        remaining = iter(files)

        def next_file():
            path = next(remaining, None)
            if path is not None:
                load(path, "")
                return
            if panel == self.editor_view:
                from PySide6.QtGui import QImage

                self.editor.pending_images = [QImage(str(path)) for path in images]
                self.editor.set_document(ordered)
                self.editor_status()
            else:
                self.workspace.add_pages(ordered)

        def load(path, password):
            def done(total, error):
                if isinstance(error, PasswordRequired):
                    value, ok = ask_text(
                        self,
                        "Password protected PDF",
                        tr(self, "Password for {name}", name=path.name),
                        QLineEdit.EchoMode.Password,
                    )
                    if ok:
                        load(path, value)
                elif isinstance(error, Cancelled):
                    self.notice(message_for(error))
                elif error:
                    self.alert(message_for(error))
                else:
                    indexes = range(total)
                    if choose_range:
                        answer, ok = ask_text(
                            self,
                            "Insert a page range",
                            tr(
                                self,
                                "{name} has {total} pages. Enter a range such as 1-3,5.",
                                name=path.name,
                                total=total,
                            ),
                        )
                        if not ok:
                            return
                        try:
                            indexes = page_range(answer, total)
                        except ValueError as invalid:
                            self.alert(str(invalid))
                            return
                    ordered.extend(Page(path, i, password) for i in indexes)
                    next_file()

            def work(cancelled, _):
                check_cancelled(cancelled)
                total = inspect(path, password)
                check_cancelled(cancelled)
                return total

            self.run_job(work, "Opening PDF…", done)

        next_file()

    def editor_status(self):
        name = self.editor.references[0].path.name if self.editor.references else ""
        status = tr(self, "Unsaved changes")
        self.editor_label.setText(f"{name}  •  {status}" if self.editor.dirty else name)

    def save_current(self):
        panel = self.stack.currentWidget()
        if panel == self.editor_view:
            self.save_editor()
        elif panel == self.workspace:
            self.run_workspace()

    def destination(self, suggested=None):
        folder = self.prefs.value("folder", "")
        if suggested is None:
            found = QFileDialog.getExistingDirectory(self, tr(self, "Choose output folder"), folder)
        else:
            initial = str(Path(folder) / suggested) if folder else suggested
            found, _ = QFileDialog.getSaveFileName(
                self, tr(self, "Save as PDF"), initial, tr(self, "PDF files (*.pdf)")
            )
            if found and not found.lower().endswith(".pdf"):
                found += ".pdf"
        if found:
            path = Path(found)
            if safe_local(path):
                return path
            self.alert("Choose an output location on this computer.")
        return None

    def run_workspace(self):
        if self.busy:
            return
        try:
            multi, groups = self.workspace.output_plan()
        except ValueError as error:
            self.alert(str(error))
            return
        target = self.destination(None if multi else "PDF Toolbox.pdf")
        if target:
            self.run_job(
                self.workspace.create_job(target, multi, groups),
                "Exporting PDF pages…",
                self.export_done,
            )

    def save_editor(self, *, after=None):
        if not self.editor.references or self.busy:
            return
        target = self.destination(f"{self.editor.references[0].path.stem}-edited.pdf")
        if not target:
            return
        pages = list(self.editor.references)
        state = self.editor.objects
        sizes = dict(self.editor.sizes)

        def work(cancelled, progress):
            from .editor import make_overlay
            from .pdf import check_cancelled

            overlays = {}
            for index, objects in state.items():
                check_cancelled(cancelled)
                overlays[index] = make_overlay(objects, *sizes[index])
            return [
                export(pages, target, cancelled=cancelled, progress=progress, overlays=overlays)
            ]

        def done(result, error):
            if not error:
                self.editor.saved = state
                self.editor_status()
            if not error and after:
                after()
            else:
                self.export_done(result, error)

        self.run_job(work, "Saving edited PDF…", done)

    def resolve_editor(self, proceed, *, allow_discard=True):
        if not self.editor.dirty:
            proceed()
            return
        buttons = [QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Cancel]
        if allow_discard:
            buttons.append(QMessageBox.StandardButton.Discard)
        selected = self.question(
            "Save changes?",
            "The PDF has unsaved edits.",
            QMessageBox.StandardButton.Save,
            *buttons,
        )
        if selected == QMessageBox.StandardButton.Save:
            self.save_editor(after=proceed)
        elif selected == QMessageBox.StandardButton.Discard:
            proceed()

    def run_job(self, work, label, done):
        if self.busy:
            return
        self.stack.setEnabled(False)
        self.notice(label, 0)
        self.progress.setRange(0, 0)
        self.progress.show()
        self.cancel.show()

        def finish(value, error):
            self.busy = None
            self.stack.setEnabled(True)
            self.statusBar().clearMessage()
            if not self.update_running:
                self.progress.hide()
                self.cancel.hide()
            done(value, error)

        self.busy = self.jobs.submit(work, finish, self.progress_value)

    def progress_value(self, current, total):
        self.progress.setRange(0, 100)
        self.progress.setValue(round(100 * current / max(1, total)))

    def cancel_work(self):
        if self.busy:
            self.busy.set()
        elif self.update_running:
            self.update_running.set()
        self.notice("Cancelling…", 0)

    def export_done(self, results, error):
        if error:
            if type(error).__name__ == "Cancelled":
                self.notice(message_for(error))
            else:
                self.alert(message_for(error))
            return
        box = QMessageBox(
            QMessageBox.Icon.Information,
            tr(self, "Export complete"),
            tr(self, "Saved {count} file(s).", count=len(results)),
            parent=self,
        )
        folder = box.addButton(tr(self, "Open folder"), QMessageBox.ButtonRole.ActionRole)
        file = (
            box.addButton(tr(self, "Open file"), QMessageBox.ButtonRole.ActionRole)
            if len(results) == 1
            else None
        )
        box.addButton(QMessageBox.StandardButton.Close)
        localize_buttons(box, QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() == folder:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(results[0].parent)))
        elif file and box.clickedButton() == file:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(results[0])))

    def clear_cache(self):
        self.workspace.thumbnails.clear()
        self.editor.thumbnails.clear()
        self.notice("Preview cache cleared.")

    def notice(self, text, timeout=8000):
        self.statusBar().showMessage(tr(self, text), timeout)

    def alert(self, text):
        button = QMessageBox.StandardButton.Ok
        box = QMessageBox(QMessageBox.Icon.Warning, "PDF Toolbox", tr(self, text), button, self)
        box.setTextFormat(Qt.TextFormat.PlainText)
        localize_buttons(box, button)
        box.exec()

    def question(self, title, text, default, *buttons):
        box = QMessageBox(QMessageBox.Icon.Question, tr(self, title), tr(self, text), parent=self)
        for button in buttons:
            box.addButton(button)
        localize_buttons(box, *buttons)
        box.setDefaultButton(default)
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.exec()
        clicked = box.clickedButton()
        return box.standardButton(clicked) if clicked else QMessageBox.StandardButton.NoButton

    def confirm(self, title, text):
        return (
            self.question(
                title,
                text,
                QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        )

    def about(self):
        box = QMessageBox(
            QMessageBox.Icon.Information,
            tr(self, "About PDF Toolbox"),
            f"PDF Toolbox {VERSION}\n" + tr(self, "Local desktop PDF tools"),
            parent=self,
        )
        update = box.addButton(tr(self, "Check for updates"), QMessageBox.ButtonRole.ActionRole)
        licenses = box.addButton(tr(self, "Licenses"), QMessageBox.ButtonRole.ActionRole)
        guide = box.addButton(tr(self, "User guide"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        localize_buttons(box, QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() == update:
            self.check_updates(manual=True)
        elif box.clickedButton() == licenses:
            file = RESOURCE / "THIRD_PARTY_LICENSES.md"
            if file.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file)))
        elif box.clickedButton() == guide:
            filename = "USER_GUIDE_TH.md" if thai_enabled(self) else "USER_GUIDE.md"
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(RESOURCE / filename)))

    def check_updates(self, *, manual):
        if self.update_running or self.update_button.isVisible():
            return
        if not manual:
            if not self.prefs.value("auto_updates", False, type=bool):
                return
            interval = self.prefs.value("interval", 24, type=int) * 3600
            if time.time() - self.prefs.value("last_attempt", 0, type=float) < interval:
                return
        if not self.update_config:
            status = "Updates are unavailable for this build."
            self.update_status(status)
            if manual:
                self.notice(status)
            return
        self.prefs.setValue("last_attempt", time.time())

        def work(*_):
            return self.client().check(VERSION)

        def done(release, error):
            self.update_running = None
            if error:
                status = (
                    str(error)
                    if isinstance(error, UpdateError)
                    else "Update check could not finish."
                )
                self.update_status(status)
                if manual:
                    self.notice(status)
                return
            if not release:
                self.update_status("This version is current.")
                if manual:
                    self.notice("This version is current.")
                return
            if not manual and release.manifest.version == self.prefs.value("skipped", ""):
                self.update_status("The available version was skipped.")
                return
            self.release = release
            self.update_status(f"Version {release.manifest.version} is available.")
            self.update_button.show()
            if manual and not self.busy:
                self.offer_update()

        self.update_running = self.update_jobs.submit(work, done)

    def client(self):
        config = self.update_config
        if config is None:
            raise UpdateError("Updates are unavailable for this build.")
        token = Credentials(config.repository).read() if config.private else ""
        return GitHub(config, token)

    def update_status(self, text):
        self.prefs.setValue("update_status", text)
        self.settings.status.setText(tr(self, text))

    def offer_update(self):
        if self.busy or self.update_running or not self.release:
            return
        if self.installer:
            self.install_update()
            return
        release = self.release
        details = release.manifest
        box = QMessageBox(
            QMessageBox.Icon.Information,
            tr(self, "Update available"),
            tr(
                self,
                "Installed {installed} • Available {latest}",
                installed=VERSION,
                latest=details.version,
            )
            + "\n"
            f"{details.date} • {details.size / 1048576:.1f} MB",
            parent=self,
        )
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setDetailedText(release.notes)
        if release.notes and thai_enabled(self):
            for button in box.buttons():
                if button.text() in {"Show Details...", "Show Details…"}:
                    button.setText(tr(self, "Show Details…"))
                    button.clicked.connect(
                        lambda _, details_button=button: details_button.setText(
                            tr(self, details_button.text().replace("...", "…"))
                        )
                    )
                    break
        now = box.addButton(tr(self, "Update now"), QMessageBox.ButtonRole.AcceptRole)
        later = box.addButton(tr(self, "Later"), QMessageBox.ButtonRole.RejectRole)
        skip = box.addButton(tr(self, "Skip this version"), QMessageBox.ButtonRole.ActionRole)
        box.setDefaultButton(later)
        box.exec()
        if box.clickedButton() == skip:
            self.prefs.setValue("skipped", details.version)
            self.update_button.hide()
        elif box.clickedButton() == now:
            self.download_update()
        elif box.clickedButton() == later:
            self.update_button.hide()

    def download_update(self):
        release = self.release
        self.progress.setRange(0, 0)
        self.progress.show()
        self.cancel.show()
        self.notice("Downloading verified update…", 0)

        def work(event, progress):
            return self.client().download(release, data_path() / "updates", event, progress)

        def progress(current, total):
            if not self.busy:
                self.progress_value(current, total)
                self.notice(
                    tr(
                        self,
                        "Downloaded {current:.1f} of {total:.1f} MB",
                        current=current / 1048576,
                        total=total / 1048576,
                    ),
                    0,
                )

        def done(path, error):
            self.update_running = None
            if not self.busy:
                self.progress.hide()
                self.cancel.hide()
            if error:
                self.notice(
                    str(error)
                    if isinstance(error, UpdateError)
                    else "Update download ended before installation."
                )
            else:
                self.installer = path
                self.update_button.setText(tr(self, "Ready to install"))
                self.notice("Update verified. Select Ready to install when you’re ready.")

        self.update_running = self.update_jobs.submit(work, done, progress)

    def install_update(self):
        if self.busy or not self.installer or not self.release:
            return
        installer, release = self.installer, self.release
        if not self.confirm(
            "Install update?", "PDF Toolbox will close and start the verified installer."
        ):
            return

        def launch():
            try:
                verify_file(
                    installer,
                    release.manifest,
                    self.update_config.require_authenticode if self.update_config else False,
                )
            except (OSError, UpdateError):
                self.installer = None
                self.update_button.setText(tr(self, "Update available"))
                self.discard_download(installer)
                self.statusBar().clearMessage()
                self.alert("The downloaded installer could not be verified. Download it again.")
                return
            try:
                self.prefs.setValue("pending_upgrade", release.manifest.version)
                self.prefs.setValue("upgrade_installer", str(installer))
                self.prefs.sync()
                subprocess.Popen([str(installer), f"/WAITPID={os.getpid()}"])
            except OSError:
                self.prefs.remove("pending_upgrade")
                self.prefs.remove("upgrade_installer")
                self.alert("The installer could not start. Try again.")
                return
            self.close_approved = True
            self.close()

        self.resolve_editor(launch, allow_discard=False)

    def confirm_upgrade(self):
        pending = self.prefs.value("pending_upgrade", "")
        if not pending:
            return
        self.prefs.remove("pending_upgrade")
        stored = self.prefs.value("upgrade_installer", "")
        self.prefs.remove("upgrade_installer")
        if pending == VERSION:
            self.notice(tr(self, "Updated to {version}.", version=VERSION))
            self.discard_download(Path(stored))
        else:
            self.notice("The update did not complete. You can continue using this version.")

    @staticmethod
    def discard_download(path):
        if (
            path.name == "PDF-Toolbox-Setup-x64.exe"
            and path.parent.parent == data_path() / "updates"
        ):
            try:
                path.unlink(missing_ok=True)
                path.parent.rmdir()
            except OSError:
                pass

    def closeEvent(self, event):
        if self.busy:
            self.notice("Wait for the current PDF operation to finish or cancel it first.")
            event.ignore()
        elif self.update_running:
            self.update_running.set()
            self.notice("Wait for the update task to finish before closing.")
            event.ignore()
        elif self.editor.dirty and not self.close_approved:
            event.ignore()

            def proceed():
                self.close_approved = True
                QTimer.singleShot(0, self.close)

            self.resolve_editor(proceed)
        else:
            self.update_timer.stop()
            self.workspace.thumbnails.timer.stop()
            self.workspace.document_previews.timer.stop()
            self.editor.thumbnails.timer.stop()
            self.thumbs.cancel_all()
            self.jobs.cancel_all()
            self.prefs.sync()
            event.accept()


def main():
    app = QApplication(sys.argv)
    smoke = "--smoke-test" in sys.argv
    if smoke:
        QStandardPaths.setTestModeEnabled(True)
    app.setApplicationName("PDF Toolbox")
    app.setApplicationVersion(VERSION)
    app.setWindowIcon(QIcon(str(RESOURCE / "resources/pdf-toolbox.ico")))
    app.setStyle("Fusion")
    load_fonts(RESOURCE)
    window = Window()
    window.show()
    if smoke:
        window.update_timer.stop()
        verify_bundled_runtime()
        QTimer.singleShot(600, window.close)
    return app.exec()


def verify_bundled_runtime():
    from contextlib import closing
    from tempfile import TemporaryDirectory

    from pypdf import PdfReader, PdfWriter

    from .editor import Object, make_overlay
    from .pdf import locked_page, render

    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.pdf"
        output = root / "output.pdf"
        writer = PdfWriter()
        writer.add_blank_page(100, 100)
        writer.write(source)
        text = "PDF เก้าอี้"
        stamp = make_overlay([Object("Text", 8, 12, 90, 40, text=text)], 100, 100)
        export([Page(source, 0)], output, overlays={0: stamp})
        reader = PdfReader(output)
        if "PDF" not in reader.pages[0].extract_text():
            raise RuntimeError("Packaged text export failed")
        with locked_page(Page(output, 0)) as page, closing(page.get_textpage()) as textpage:
            if text not in textpage.get_text_range():
                raise RuntimeError("Packaged Thai text extraction failed")
        if render(Page(output, 0), dpi=72).size != (100, 100):
            raise RuntimeError("Packaged page rendering failed")
