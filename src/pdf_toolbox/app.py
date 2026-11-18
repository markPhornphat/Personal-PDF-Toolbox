from __future__ import annotations

import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QSize, QStandardPaths
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QActionGroup, QColor, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QFileDialog,
    QGraphicsOpacityEffect,
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

from .appearance import (
    DARK,
    LIGHT,
    Mascot,
    ToolCard,
    action_button,
    load_display_font,
    motion_enabled,
    stylesheet,
    tool_icon,
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
from .localization import (
    ask_text,
    describe_button,
    describe_buttons,
    localize_buttons,
    retranslate_controls,
    thai_enabled,
    tr,
)
from .progress import ProcessingDialog
from .settings import Settings, data_path, preferences
from .updater import Config, Credentials, GitHub, UpdateError, verify_file
from .update_ui import UpdateNotice, startup_check_key
from .viewer import local_paths
from .workspace import ORGANIZE, TOOLS, Workspace

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
    "Reorder, rotate and insert pages",
)
IMAGE_TYPES = {".png", ".jpg", ".jpeg"}
TOOL_ICONS = ("merge", "split", "extract", "image", "edit", "organize")
NAV_ICONS = dict(
    zip(
        ("Home", *TOOLS, "Settings", "About"),
        ("home", *TOOL_ICONS, "settings", "about"),
        strict=True,
    )
)
TOOL_TONES = ("pistachio", "rose", "lilac", "butter", "rose", "organize")


class FileDropFrame(QFrame):
    files = Signal(list)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)

    def highlight(self, value):
        self.setProperty("dragging", value)
        self.style().unpolish(self)
        self.style().polish(self)

    def dragEnterEvent(self, event):
        if local_paths(event.mimeData()):
            self.highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.highlight(False)
        super().dragLeaveEvent(event)

    def dropEvent(self, event):
        self.highlight(False)
        paths = local_paths(event.mimeData())
        if paths:
            self.files.emit(paths)
            event.acceptProposedAction()


class DropArea(FileDropFrame):
    def __init__(self, browse):
        super().__init__()
        self.setObjectName("DropArea")
        self.setMinimumHeight(307)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(33, 13, 19, 13)
        layout.setSpacing(8)
        copy = QVBoxLayout()
        copy.setSpacing(9)
        headline = QLabel("Drop a file to\nget started")
        headline.setObjectName("HeroTitle")
        headline.setWordWrap(True)
        tip = QLabel("PDF, JPG or PNG. Paste files with Ctrl+V.")
        tip.setObjectName("HeroHint")
        tip.setWordWrap(True)
        choose = action_button("folder", "Browse files…", primary=True)
        choose.setObjectName("BrowsePrimary")
        choose.clicked.connect(browse)
        copy.addStretch()
        copy.addWidget(headline)
        copy.addWidget(tip)
        copy.addSpacing(5)
        copy.addWidget(choose, alignment=Qt.AlignmentFlag.AlignLeft)
        copy.addStretch()
        layout.addLayout(copy, 3)
        self.mascot = Mascot(RESOURCE / "resources/paper-dog.png")
        layout.addWidget(self.mascot, 2)


class EmptyTool(QWidget):
    def __init__(self, browse):
        super().__init__()
        self.tool = TOOLS[0]
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)
        layout.addStretch(2)
        center = Qt.AlignmentFlag.AlignHCenter
        self.icon = QLabel()
        self.icon.setObjectName("EmptyToolIcon")
        self.icon.setFixedSize(80, 80)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_opacity = QGraphicsOpacityEffect(self.icon, opacity=1.0)
        self.icon.setGraphicsEffect(self.icon_opacity)
        self.reveal = QPropertyAnimation(self.icon_opacity, b"opacity", self)
        self.reveal.setDuration(160)
        self.reveal.setStartValue(0.25)
        self.reveal.setEndValue(1.0)
        self.reveal.setEasingCurve(QEasingCurve.Type.OutCubic)
        layout.addWidget(self.icon, alignment=center)
        self.title = QLabel()
        self.title.setObjectName("EmptyToolTitle")
        self.description = QLabel()
        self.description.setObjectName("HeroHint")
        for label in (self.title, self.description):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addSpacing(14)

        self.drop = FileDropFrame()
        self.drop.setObjectName("ToolDropArea")
        self.drop.setMaximumWidth(534)
        field = QVBoxLayout(self.drop)
        field.setContentsMargins(24, 22, 24, 23)
        field.setSpacing(12)
        self.hint = QLabel()
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint.setWordWrap(True)
        field.addWidget(self.hint)
        self.choose = action_button("folder", "Browse files…", primary=True)
        self.choose.setObjectName("BrowsePrimary")
        self.choose.clicked.connect(browse)
        field.addWidget(self.choose, alignment=center)
        layout.addWidget(self.drop)
        layout.setAlignment(self.drop, center)
        self.drop.setMinimumWidth(416)
        layout.addStretch(3)

    def refresh(self, palette):
        index = TOOLS.index(self.tool)
        self.icon.setProperty("tone", TOOL_TONES[index])
        self.icon.style().unpolish(self.icon)
        self.icon.style().polish(self.icon)
        ink = palette["organize_ink"] if self.tool == ORGANIZE else palette["primary"]
        self.icon.setPixmap(tool_icon(TOOL_ICONS[index], ink, 40).pixmap(40, 40))
        self.title.setText(tr(self, self.tool))
        self.description.setText(tr(self, DESCRIPTIONS[index]))
        single = self.tool in {TOOLS[1], TOOLS[4]}
        self.hint.setText(tr(self, "Drop a PDF here" if single else "Drop one or more PDFs here"))

    def animate_icon(self):
        self.reveal.stop()
        if motion_enabled(self):
            self.reveal.start()
        else:
            self.icon_opacity.setOpacity(1.0)


class Window(QMainWindow):
    def __init__(self, prefs=None):
        super().__init__()
        load_display_font(RESOURCE)
        self.setWindowTitle(f"PDF Toolbox {VERSION}")
        self.resize(1260, 790)
        self.setMinimumSize(980, 650)
        self.setAcceptDrops(True)
        self.prefs = prefs if prefs is not None else preferences()
        self.jobs = Jobs(self)
        self.thumbs = Jobs(self, threads=1)
        self.update_jobs = Jobs(self, threads=1)
        self.busy = None
        self.processing = None
        self.update_running = None
        self.update_notice = None
        self.update_reminded_later = False
        self.update_dialog = None
        self.about_dialog = None
        self.about_check = None
        self.startup_update_key = startup_check_key()
        self.release = None
        self.installer = None
        self.close_approved = False
        self.translation = {}
        self.update_config = self.load_config()

        self.stack = QStackedWidget()
        self.home = self.build_home()
        self.suggestion_menu = QMenu(self)
        self.suggestion_menu.setToolTipsVisible(True)
        self.workspace = Workspace(self.jobs, self.thumbs)
        self.editor = Editor(self.jobs, self.thumbs)
        self.editor_view = self.build_editor()
        self.empty_tool = EmptyTool(self.browse)
        self.settings = Settings(self)
        for panel in [self.home, self.workspace, self.editor_view, self.empty_tool, self.settings]:
            self.stack.addWidget(panel)
        self.workspace.browse.connect(self.browse)
        self.workspace.browse_range.connect(self.browse_range)
        self.workspace.add_files.connect(self.accept_files)
        self.workspace.pages_changed.connect(self.refresh_tool_page)
        self.empty_tool.drop.files.connect(self.accept_files)
        self.workspace.failed.connect(self.alert)
        self.workspace.run_requested.connect(self.run_workspace)
        self.editor.alert.connect(self.alert)
        self.editor.open_requested.connect(self.accept_files)
        self.editor.changed.connect(self.editor_status)

        main = QWidget()
        columns = QHBoxLayout(main)
        columns.setContentsMargins(17, 17, 20, 5)
        columns.setSpacing(19)
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(208)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(12, 17, 12, 13)
        nav.setSpacing(5)
        identity = QHBoxLayout()
        identity.setSpacing(8)
        self.brand_mark = QLabel()
        self.brand_mark.setObjectName("BrandMark")
        self.brand_mark.setFixedSize(33, 35)
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand = QLabel("PDF Toolbox")
        brand.setObjectName("Brand")
        identity.addWidget(self.brand_mark)
        identity.addWidget(brand, 1)
        nav.addLayout(identity)
        self.version_label = QLabel()
        self.version_label.setObjectName("Muted")
        nav.addSpacing(17)
        self.nav_buttons = {}
        for index, (label, action) in enumerate(
            [
                ("Home", lambda: self.show_panel(self.home)),
                *[(tool, lambda _checked, name=tool: self.select_tool(name)) for tool in TOOLS],
                ("Settings", lambda: self.show_panel(self.settings)),
                ("About", self.about),
            ]
        ):
            if index == len(TOOLS) + 1:
                nav.addStretch()
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setIconSize(QSize(20, 20))
            button.clicked.connect(action)
            self.nav_buttons[label] = button
            if label == "Settings":
                row = QHBoxLayout()
                row.setSpacing(4)
                row.addWidget(button, 1)
                row.addWidget(self.build_theme_button(), 0, Qt.AlignmentFlag.AlignVCenter)
                nav.addLayout(row)
            else:
                nav.addWidget(button)
        self.update_button = QPushButton("Update available")
        self.update_button.clicked.connect(self.offer_update)
        self.update_button.hide()
        nav.addWidget(self.update_button)
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedHeight(1)
        nav.addSpacing(3)
        nav.addWidget(divider)
        nav.addWidget(self.version_label)
        columns.addWidget(sidebar)
        columns.addWidget(self.stack, 1)
        self.setCentralWidget(main)
        self.stack.currentChanged.connect(self.refresh_navigation)

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
        self.refresh_navigation()
        self.update_timer = QTimer(self)
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(2000)
        self.update_timer.timeout.connect(lambda: self.check_updates(manual=False))
        self.update_timer.start()
        QTimer.singleShot(0, self, self.confirm_upgrade)

    def build_home(self):
        home = QWidget()
        layout = QVBoxLayout(home)
        layout.setContentsMargins(0, 0, 0, 6)
        layout.setSpacing(13)
        self.drop = DropArea(self.browse)
        self.drop.files.connect(self.accept_files)
        layout.addWidget(self.drop)
        tools = QHBoxLayout()
        label = QLabel("PDF tools")
        label.setObjectName("Section")
        tools.addWidget(label, 1)
        self.search = QLineEdit()
        self.search.setObjectName("ToolSearch")
        self.search.setMaximumWidth(238)
        self.search.setMinimumWidth(205)
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search tools")
        self.search.setPlaceholderText("Search tools")
        self.search.textChanged.connect(self.filter_tools)
        tools.addWidget(self.search)
        layout.addSpacing(6)
        layout.addLayout(tools)
        self.tool_grid = QGridLayout()
        self.tool_grid.setSpacing(11)
        for column in range(3):
            self.tool_grid.setColumnStretch(column, 1)
        self.cards = []
        for name, detail, kind, tone in zip(
            TOOLS, DESCRIPTIONS, TOOL_ICONS, TOOL_TONES, strict=True
        ):
            button = ToolCard(name, detail, kind, tone, featured=name == ORGANIZE)
            button.setParent(home)
            button.clicked.connect(lambda _, tool=name: self.select_tool(tool))
            self.cards.append(button)
        layout.addLayout(self.tool_grid)
        self.no_tool_results = QLabel("No tools match your search.")
        self.no_tool_results.setObjectName("NoToolResults")
        layout.addWidget(self.no_tool_results)
        layout.addStretch(1)
        self.filter_tools("")
        order = [self.search, *self.cards]
        for first, second in zip(order, order[1:]):
            QWidget.setTabOrder(first, second)
        return home

    def build_theme_button(self):
        button = QPushButton()
        button.setObjectName("ThemeButton")
        button.setIconSize(QSize(19, 19))
        button.setFixedSize(36, 36)
        button.setAccessibleName("Theme")
        menu = QMenu(button)
        menu.setToolTipsVisible(True)
        group = QActionGroup(menu)
        self.theme_actions = {}
        for theme in ("System", "Light", "Dark"):
            action = menu.addAction(theme)
            action.setCheckable(True)
            group.addAction(action)
            action.triggered.connect(
                lambda _checked, value=theme: self.settings.theme.setCurrentText(value)
            )
            self.theme_actions[theme] = action
        button.clicked.connect(lambda: menu.popup(button.mapToGlobal(button.rect().bottomLeft())))
        self.theme_button = button
        return button

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
        for label, icon, slot in [
            ("Browse files…", "folder", self.browse),
            ("Save", "save", self.save_editor),
            ("Save as…", "export", self.save_editor),
        ]:
            button = action_button(icon, label, primary=label == "Save as…")
            button.clicked.connect(slot)
            buttons.addWidget(button)
        panel.addLayout(buttons)
        panel.addWidget(self.editor)
        return wrap

    def install_shortcuts(self):
        self.search.installEventFilter(self)
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
        palette = DARK if theme == "Dark" or (theme == "System" and system) else LIGHT
        self.theme_palette = palette
        self.setStyleSheet(stylesheet(palette))
        for label, button in self.nav_buttons.items():
            button.setIcon(tool_icon(NAV_ICONS[label], palette["primary"]))
        for button in self.findChildren(QPushButton):
            kind = button.property("iconKind")
            if kind:
                color = palette["on_primary"] if button.property("primary") else palette["primary"]
                button.setIcon(tool_icon(kind, color))
        self.brand_mark.setPixmap(tool_icon("paper", palette["on_primary"]).pixmap(22, 22))
        for card in self.cards:
            card.set_icon_color(
                palette["organize_ink"] if card.kind == "organize" else palette["primary"]
            )
        for value, action in self.theme_actions.items():
            action.setChecked(value == theme)
        self.theme_button.setIcon(
            tool_icon("moon" if palette is DARK else "sun", palette["primary"])
        )
        self.empty_tool.refresh(palette)
        self.drop.mascot.backing = QColor(palette["art"])
        self.drop.mascot.update()

    def translate(self):
        retranslate_controls(self)
        self.search.setAccessibleName(tr(self, "Search tools"))
        self.drop.mascot.setAccessibleName(tr(self, "Dog with an ice cream cone"))
        for value, action in self.theme_actions.items():
            action.setText(tr(self, value))
            describe_button(action, self, value)
        self.empty_tool.refresh(self.theme_palette)
        for card in self.cards:
            card.refresh_accessibility()
        self.filter_tools(self.search.text())
        self.version_label.setText(tr(self, "Version {version}", version=VERSION))
        self.update_button.setText(tr(self, "Update available"))
        self.settings.status.setText(
            tr(self, self.prefs.value("update_status", "No update checks yet"))
        )
        self.workspace.retranslate()
        self.editor.retranslate()
        self.editor_status()
        describe_buttons(self, self)
        describe_button(self.settings.folder, self, "Choose folder…")

    def filter_tools(self, query):
        query = query.casefold().strip()
        visible = [card for card in self.cards if card.matches(query)]
        for card in self.cards:
            self.tool_grid.removeWidget(card)
            card.setVisible(card in visible)
        for index, card in enumerate(visible):
            self.tool_grid.addWidget(card, index // 3, index % 3)
        self.no_tool_results.setVisible(not visible)
        rows = (len(visible) + 2) // 3
        for row in range(2):
            self.tool_grid.setRowMinimumHeight(row, 105 if row < rows else 0)

    def refresh_navigation(self):
        panel = self.active_panel()
        if panel is self.workspace:
            active = self.workspace.mode
        else:
            active = {self.home: "Home", self.settings: "Settings", self.editor_view: TOOLS[4]}.get(
                panel
            )
        for name, button in self.nav_buttons.items():
            selected = name == active
            if button.property("active") != selected:
                button.setProperty("active", selected)
                button.style().unpolish(button)
                button.style().polish(button)

    def show_panel(self, panel):
        if not self.busy:
            self.stack.setCurrentWidget(panel)

    def active_panel(self):
        panel = self.stack.currentWidget()
        if panel is self.empty_tool:
            return self.editor_view if self.empty_tool.tool == TOOLS[4] else self.workspace
        return panel

    def show_tool_page(self, panel):
        if panel is self.workspace:
            tool, has_pages = self.workspace.mode, self.workspace.listing.count() > 0
        else:
            tool, has_pages = TOOLS[4], bool(self.editor.references)
        if has_pages:
            self.show_panel(panel)
        else:
            changed = (
                self.empty_tool.tool != tool or self.stack.currentWidget() is not self.empty_tool
            )
            self.empty_tool.tool = tool
            self.empty_tool.refresh(self.theme_palette)
            self.show_panel(self.empty_tool)
            if changed:
                self.empty_tool.animate_icon()

    def refresh_tool_page(self):
        panel = self.active_panel()
        if panel is self.workspace or panel is self.editor_view:
            self.show_tool_page(panel)

    def select_tool(self, tool, files=None):
        if self.busy:
            self.notice("Wait for the current PDF operation to finish.")
            return
        if tool == TOOLS[4]:
            self.show_tool_page(self.editor_view)
        else:
            if self.workspace.mode != tool:
                self.workspace.configure(tool)
            self.workspace.dpi.setValue(self.prefs.value("dpi", 200, type=int))
            self.workspace.quality.setValue(self.prefs.value("quality", 90, type=int))
            self.show_tool_page(self.workspace)
        self.translate()
        self.refresh_navigation()
        if files:
            self.accept_files(files)

    def browse(self):
        panel = self.active_panel()
        single = panel is self.editor_view or (
            panel is self.workspace and self.workspace.mode == TOOLS[1]
        )
        kind = (
            "PDF and images (*.pdf *.jpg *.jpeg *.png)"
            if panel is self.home
            else "PDF files (*.pdf)"
        )
        if single:
            name, _ = QFileDialog.getOpenFileName(
                self, tr(self, "Choose files"), "", tr(self, kind)
            )
            names = [name] if name else []
        else:
            names, _ = QFileDialog.getOpenFileNames(
                self, tr(self, "Choose files"), "", tr(self, kind)
            )
        if names:
            self.accept_files([Path(name) for name in names])

    def paste(self):
        data = QApplication.clipboard().mimeData()
        if data is None:
            return
        files = local_paths(data)
        if files and self.stack.currentWidget() == self.home:
            self.accept_files(files)
            return
        focused = QApplication.focusWidget()
        if isinstance(focused, (QLineEdit, QTextEdit)):
            focused.paste()
            return
        if self.active_panel() is self.editor_view:
            self.editor.paste(data)
        elif files:
            self.accept_files(files)

    def eventFilter(self, watched, event):
        # QLineEdit normally reserves Paste for itself, including when Explorer copied files.
        if (
            watched is self.search
            and event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress)
            and event.matches(QKeySequence.StandardKey.Paste)
        ):
            data = QApplication.clipboard().mimeData()
            if data is not None and local_paths(data):
                event.accept()
                if event.type() == QEvent.Type.KeyPress:
                    self.paste()
                return True
        return super().eventFilter(watched, event)

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
        current = self.active_panel()
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
        menu = self.suggestion_menu
        menu.clear()
        choices = (TOOLS[0], TOOLS[3], ORGANIZE) if len(pdfs) > 1 else TOOLS
        for choice in choices:
            icon = tool_icon(NAV_ICONS[choice], self.theme_palette["primary"])
            action = menu.addAction(icon, tr(self, choice))
            describe_button(action, self, choice)
            action.triggered.connect(
                lambda _checked, tool=choice: QTimer.singleShot(
                    0, self, lambda: self.open_suggestion(tool, pdfs, images)
                )
            )
        menu.popup(self.drop.mapToGlobal(self.drop.rect().center()))

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
        if self.active_panel() is self.editor_view:
            self.show_tool_page(self.editor_view)

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
        self.notice(label, 0)
        dialog = ProcessingDialog(self, label, self.drop.mascot.pixmap, self.theme_palette)
        dialog.cancel_requested.connect(self.cancel_work)
        self.processing = dialog

        def finish(value, error):
            self.busy = None
            self.processing = None
            dialog.done(0)
            dialog.deleteLater()
            self.statusBar().clearMessage()
            done(value, error)
            if (
                self.release
                and not self.busy
                and not self.update_running
                and not self.update_reminded_later
            ):
                self.offer_update()

        self.busy = self.jobs.submit(work, finish, dialog.report)
        dialog.open()

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
        if self.about_dialog is not None and self.about_dialog.isVisible():
            self.about_dialog.raise_()
            return
        dialog = QDialog(self)
        self.about_dialog = dialog
        dialog.finished.connect(lambda _: self.clear_about())
        dialog.setObjectName("AboutDialog")
        dialog.setWindowTitle(tr(self, "About PDF Toolbox"))
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(13)

        hero = QFrame()
        hero.setObjectName("AboutHero")
        cover = QVBoxLayout(hero)
        cover.setContentsMargins(18, 11, 18, 20)
        cover.setSpacing(4)
        center = Qt.AlignmentFlag.AlignHCenter
        mascot = Mascot(RESOURCE / "resources/paper-dog.png")
        mascot.setAccessibleName(tr(self, "Dog with an ice cream cone"))
        mascot.setFixedSize(140, 138)
        mascot.backing = QColor(self.theme_palette["organize"])
        cover.addWidget(mascot, alignment=center)

        title = QLabel("PDF Toolbox")
        title.setObjectName("Heading")
        cover.addWidget(title, alignment=center)
        version = QLabel(tr(self, "Version {version}", version=VERSION))
        version.setObjectName("AboutVersion")
        cover.addWidget(version, alignment=center)
        description = QLabel(tr(self, "Local desktop PDF tools"))
        description.setObjectName("Muted")
        cover.addWidget(description, alignment=center)
        layout.addWidget(hero)

        def open_document(filename):
            file = RESOURCE / filename
            if file.is_file():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file)))

        def close_and_run(callback):
            dialog.accept()
            callback()

        guide = "USER_GUIDE_TH.md" if thai_enabled(self) else "USER_GUIDE.md"
        actions = QHBoxLayout()
        for name, icon, callback in [
            ("Check for updates", "rotate-right", lambda: self.check_updates(manual=True)),
            ("User guide", "paper", lambda: open_document(guide)),
            ("Licenses", "about", lambda: open_document("THIRD_PARTY_LICENSES.md")),
        ]:
            button = QPushButton(tool_icon(icon, self.theme_palette["primary"]), tr(self, name))
            describe_button(button, self, name)
            if name == "Check for updates":
                self.about_check = button
                button.clicked.connect(lambda: self.check_updates(manual=True))
            else:
                button.clicked.connect(lambda _checked, handler=callback: close_and_run(handler))
            if name == "Check for updates":
                layout.addWidget(button)
            else:
                actions.addWidget(button, 1)
        layout.addLayout(actions)
        self.about_progress = QProgressBar()
        self.about_progress.setRange(0, 0)
        self.about_progress.setTextVisible(False)
        self.about_progress.setFixedHeight(8)
        self.about_progress.setAccessibleName(tr(self, "Checking for updates…"))
        self.about_progress.hide()
        layout.addWidget(self.about_progress)
        self.about_status = QLabel()
        self.about_status.setWordWrap(True)
        layout.addWidget(self.about_status)

        close = QPushButton(tr(self, "Close"))
        describe_button(close, self, "Close")
        close.setDefault(True)
        close.clicked.connect(dialog.reject)
        layout.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        dialog.open()

    def clear_about(self):
        self.about_dialog = None
        self.about_check = None

    def update_check_feedback(self, checking, text=""):
        self.settings.check.setEnabled(not checking)
        self.settings.check.setText(
            tr(self, "Checking for updates…" if checking else "Check for updates")
        )
        if self.about_check is not None:
            self.about_check.setEnabled(not checking)
            self.about_check.setText(
                tr(self, "Checking for updates…" if checking else "Check for updates")
            )
            self.about_status.setText("" if checking else tr(self, text))
            self.about_progress.setVisible(checking)

    def check_updates(self, *, manual):
        if self.update_running:
            return
        if not manual:
            if not self.prefs.value("auto_updates", False, type=bool):
                return
            if self.prefs.value("startup_update_check", "") == self.startup_update_key:
                return
        if manual and self.release:
            self.update_reminded_later = False
            if self.about_dialog is not None:
                self.about_dialog.accept()
            self.offer_update()
            return
        if not self.update_config:
            status = "Updates are unavailable for this build."
            self.update_status(status)
            self.update_check_feedback(False, status)
            if manual:
                self.notice(status)
            return
        self.prefs.setValue("last_attempt", time.time())
        if not manual:
            self.prefs.setValue("startup_update_check", self.startup_update_key)
            self.prefs.sync()
        self.update_check_feedback(True, "Checking for updates…")

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
                self.update_check_feedback(False, status)
                if manual:
                    self.notice(status)
                return
            if not release:
                self.update_status("This version is current.")
                self.update_check_feedback(False, "This version is current.")
                if manual:
                    self.notice("This version is current.")
                return
            self.update_check_feedback(False)
            self.release = release
            self.update_status(f"Version {release.manifest.version} is available.")
            self.update_button.show()
            if not self.busy:
                if self.about_dialog is not None:
                    self.about_dialog.accept()
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
        if self.update_notice is not None:
            if self.update_notice.isVisible():
                self.update_notice.raise_()
                return
            self.update_notice.deleteLater()
        self.update_notice = UpdateNotice(self, self.release)
        self.update_notice.rejected.connect(self.remind_update_later)
        self.update_notice.position_at_corner()
        self.update_notice.show()
        self.update_notice.raise_()

    def remind_update_later(self):
        self.update_reminded_later = True

    def start_update(self):
        if self.busy or self.update_running or not self.release:
            return
        self.resolve_editor(self.download_update, allow_discard=False)

    def download_update(self):
        if self.update_running or not self.release:
            return
        if self.update_notice is not None:
            self.update_notice.hide()
        release = self.release
        dialog = ProcessingDialog(
            self,
            "Downloading and verifying update…",
            self.drop.mascot.pixmap,
            self.theme_palette,
        )
        dialog.cancel_requested.connect(self.cancel_work)
        self.update_dialog = dialog
        self.update_button.setEnabled(False)

        def work(event, progress):
            return self.client().download(release, data_path() / "updates", event, progress)

        def progress(current, total):
            dialog.report(current, total)

        def done(path, error):
            self.update_running = None
            self.update_dialog = None
            dialog.done(0)
            dialog.deleteLater()
            self.update_button.setEnabled(True)
            if error:
                status = (
                    str(error)
                    if isinstance(error, UpdateError)
                    else "Update download ended before installation."
                )
                if isinstance(error, Cancelled):
                    status = "Update cancelled."
                self.update_status(status)
                self.notice(status)
                self.offer_update()
                return
            self.installer = path
            self.install_update()

        self.update_running = self.update_jobs.submit(work, done, progress)
        dialog.open()

    def install_update(self):
        if self.busy or not self.installer or not self.release:
            return
        installer, release = self.installer, self.release
        try:
            verify_file(
                installer,
                release.manifest,
                self.update_config.require_authenticode if self.update_config else False,
            )
        except (OSError, UpdateError):
            self.installer = None
            self.discard_download(installer)
            self.statusBar().clearMessage()
            self.alert("The downloaded installer could not be verified. Download it again.")
            return
        install_folder = Path(sys.executable).parent if PACKAGED else None
        if install_folder is None:
            self.notice(
                "The verified update is ready. Automatic installation requires the installed app."
            )
            return
        try:
            self.prefs.setValue("pending_upgrade", release.manifest.version)
            self.prefs.setValue("upgrade_installer", str(installer))
            self.prefs.sync()
            language = "thai" if thai_enabled(self) else "english"
            subprocess.Popen(
                [
                    str(installer),
                    "/VERYSILENT",
                    "/SUPPRESSMSGBOXES",
                    "/NORESTART",
                    "/AUTORESTART=1",
                    f"/WAITPID={os.getpid()}",
                    f"/DIR={install_folder}",
                    f"/LANG={language}",
                ]
            )
        except OSError:
            self.prefs.remove("pending_upgrade")
            self.prefs.remove("upgrade_installer")
            self.prefs.sync()
            self.alert("The installer could not start. Try again.")
            return
        self.close_approved = True
        self.close()

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
        if window.drop.mascot.pixmap.isNull():
            raise RuntimeError("Packaged mascot artwork could not be loaded")
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
