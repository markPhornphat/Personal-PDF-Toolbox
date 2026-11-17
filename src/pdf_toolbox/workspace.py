from collections import Counter
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, QSize, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QSplitter,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .appearance import action_button, icon_button
from .localization import Choice, tr
from .pdf import BlankPage, Page, PageReference, convert, export, page_range, publish, split_groups
from .pdf import write_pdf
from .viewer import PageList, Thumbnails, Viewer, page_item, translate_page_item

ORGANIZE = "Organize PDF"
TOOLS = (
    "Merge / Append",
    "Split PDF",
    "Remove / Extract",
    "PDF to JPG / PNG",
    "Edit PDF",
    ORGANIZE,
)


class Workspace(QWidget):
    browse = Signal()
    browse_range = Signal()
    add_files = Signal(list)
    pages_changed = Signal()
    run_requested = Signal()
    failed = Signal(str)

    def __init__(self, jobs, thumbs):
        super().__init__()
        self.mode = TOOLS[0]
        self.jobs = jobs
        self.history: list[list[PageReference]] = [[]]
        self.cursor = 0
        self.refreshing = False
        self.listing = PageList()
        self.listing.setMinimumWidth(245)
        self.thumbnails = Thumbnails(self.listing, thumbs)
        self.documents = PageList()
        self.documents.setFixedHeight(113)
        self.documents.setGridSize(QSize(139, 104))
        self.documents.setIconSize(QSize(40, 51))
        self.documents.setSelectionMode(self.documents.SelectionMode.SingleSelection)
        self.document_previews = Thumbnails(self.documents, thumbs)
        self.documents.reordered.connect(self.reorder_documents)
        self.documents.files_dropped.connect(self.add_files)
        self.documents.itemDoubleClicked.connect(self.locate_document)
        self.viewer = Viewer(jobs)
        self.viewer.on_previous = lambda: self.navigate(-1)
        self.viewer.on_next = lambda: self.navigate(1)
        self.viewer.shown.connect(lambda *_: self.summarize())
        self.subtitle = QLabel()
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.listing.files_dropped.connect(self.add_files)
        self.listing.currentRowChanged.connect(self.selected_page)
        self.listing.itemSelectionChanged.connect(self.summarize)
        self.listing.model().rowsMoved.connect(self.order_changed)
        self.listing.reordered.connect(self.order_changed)
        self.groups = Choice()
        self.groups.addItems(["Individual pages", "Every N pages", "Custom ranges", "Boundaries"])
        self.groups.currentIndexChanged.connect(self.summarize)
        self.range = QLineEdit()
        self.range.textChanged.connect(self.summarize)
        self.naming = QLineEdit()
        self.naming.setPlaceholderText("Filename prefix or {n} pattern")
        self.zip = QCheckBox("Export as ZIP")
        self.fmt = Choice()
        self.fmt.addItems(["JPEG", "PNG"])
        self.fmt.currentIndexChanged.connect(self.summarize)
        self.dpi = QSpinBox()
        self.dpi.setRange(1, 2400)
        self.dpi.setValue(200)
        self.dpi.setSuffix(" DPI")
        self.dpi.valueChanged.connect(self.summarize)
        self.preset = Choice()
        self.preset.addItems(
            ["Custom", "72 DPI", "96 DPI", "150 DPI", "200 DPI", "300 DPI", "600 DPI"]
        )
        self.preset.setCurrentText("200 DPI")
        self.preset.currentIndexChanged.connect(
            lambda _: self.set_preset(self.preset.currentData())
        )
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(90)
        self.quality.setPrefix("JPG quality ")
        self.transparent = QCheckBox("Transparent PNG")
        self.action = Choice()
        self.action.addItems(
            [
                "Save page order",
                "Remove selected",
                "Extract selected",
                "Extract selected separately",
            ]
        )
        self.action.currentIndexChanged.connect(self.summarize)
        self.position = Choice()
        self.position.addItems(["Append at end", "Insert before current page"])
        self.export_button = action_button("export", "Export…", primary=True)
        self.export_button.clicked.connect(self.run_requested)

        outer = QVBoxLayout(self)
        top = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("Heading")
        top.addWidget(self.title)
        top.addStretch()
        self.button(top, "Add PDFs…", self.browse.emit, "folder")
        self.insert_range = self.button(top, "Add a page range…", self.browse_range.emit, "range")
        outer.addLayout(top)
        outer.addWidget(self.subtitle)

        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.documents_heading = QLabel("Documents")
        self.documents_heading.setObjectName("Section")
        left_layout.addWidget(self.documents_heading)
        left_layout.addWidget(self.documents)
        pages_heading = QLabel("Pages")
        pages_heading.setObjectName("Section")
        left_layout.addWidget(pages_heading)
        left_layout.addWidget(self.listing)
        rows = QHBoxLayout()
        for label, callback, icon in [
            ("Move up", lambda: self.move(-1), "up"),
            ("Move down", lambda: self.move(1), "down"),
            ("Duplicate", self.duplicate, "merge"),
            ("Remove", self.remove, "delete"),
        ]:
            self.button(rows, label, callback, icon, compact=icon in {"up", "down"})
        left_layout.addLayout(rows)
        rows = QHBoxLayout()
        for label, callback, icon in [
            ("Invert", self.invert, "invert"),
            ("Undo", self.undo, "undo"),
            ("Redo", self.redo, "redo"),
            ("Split here", self.add_boundary, "split"),
            ("Use range", self.select_range, "range"),
        ]:
            button = self.button(rows, label, callback, icon, compact=icon in {"undo", "redo"})
            if label == "Split here":
                self.mark = button
            if label == "Use range":
                self.pick_range = button
        left_layout.addLayout(rows)
        self.organize_toolbar = QWidget()
        actions = QHBoxLayout(self.organize_toolbar)
        actions.setContentsMargins(0, 0, 0, 0)
        for label, callback, icon in [
            ("Rotate left", lambda: self.rotate_pages(-90), "rotate-left"),
            ("Rotate right", lambda: self.rotate_pages(90), "rotate-right"),
            ("Blank page", self.insert_blank, "blank"),
            ("Reverse order", self.reverse_order, "reverse"),
        ]:
            self.button(actions, label, callback, icon, compact=icon.startswith("rotate"))
        actions.addStretch()
        left_layout.addWidget(self.organize_toolbar)
        split.addWidget(left)
        split.addWidget(self.viewer)
        split.setSizes([400, 700])
        outer.addWidget(split, 1)
        settings = QHBoxLayout()
        for control in [
            self.position,
            self.action,
            self.groups,
            self.fmt,
            self.preset,
            self.dpi,
            self.quality,
            self.transparent,
        ]:
            settings.addWidget(control)
        outer.addLayout(settings)
        export_row = QHBoxLayout()
        for control in [self.range, self.naming, self.zip, self.export_button]:
            export_row.addWidget(control)
        outer.addLayout(export_row)
        outer.addWidget(self.summary)
        self.configure(self.mode)

    @staticmethod
    def button(layout, label, callback, icon, *, compact=False):
        button = icon_button(icon, label) if compact else action_button(icon, label)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def set_preset(self, text):
        if text != "Custom":
            self.dpi.setValue(int(text.split()[0]))

    def configure(self, mode):
        self.mode = mode
        self.title.setText(mode)
        self.subtitle.setText(
            {
                TOOLS[0]: "Drop PDFs, arrange the pages, then export the combined document.",
                TOOLS[1]: "Drop a PDF and choose how to divide it into separate files.",
                TOOLS[2]: "Select pages to remove or extract. Drag pages to change their order.",
                TOOLS[3]: "Drop PDFs, select pages, and choose an image format and resolution.",
                ORGANIZE: "Drag to reorder pages, rotate selections, or insert a blank page.",
            }[mode]
        )
        self.position.setVisible(mode in {TOOLS[0], TOOLS[2], ORGANIZE})
        self.documents.setVisible(mode == TOOLS[0])
        self.documents_heading.setVisible(mode == TOOLS[0])
        self.insert_range.setVisible(mode in {TOOLS[0], ORGANIZE})
        self.organize_toolbar.setVisible(mode == ORGANIZE)
        self.action.setVisible(mode == TOOLS[2])
        for control in [self.groups, self.mark]:
            control.setVisible(mode == TOOLS[1])
        for control in [self.fmt, self.dpi, self.preset, self.quality, self.transparent]:
            control.setVisible(mode == TOOLS[3])
        self.pick_range.setVisible(mode != TOOLS[1])
        self.range.clear()
        self.naming.clear()
        self.zip.setChecked(False)
        self.history = [[]]
        self.cursor = 0
        self.thumbnails.clear()
        self.document_previews.clear()
        self.rebuild()

    def pages(self):
        return [
            self.listing.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.listing.count())
        ]

    def selected(self):
        return sorted(self.listing.row(item) for item in self.listing.selectedItems())

    def select_range(self):
        try:
            chosen = set(page_range(self.range.text(), self.listing.count()))
        except ValueError as error:
            self.failed.emit(str(error))
            return
        for index in range(self.listing.count()):
            self.listing.item(index).setSelected(index in chosen)
        self.range.clear()

    def add_pages(self, pages):
        if self.mode == TOOLS[1] and self.listing.count():
            self.failed.emit("Split handles one PDF at a time. Remove the current pages first.")
            return
        position = self.listing.currentRow()
        ordered = self.pages()
        if self.position.currentIndex() == 0 or position < 0:
            position = len(ordered)
        ordered[position:position] = pages
        self.remember(ordered)
        self.rebuild(position)

    def remember(self, ordered):
        if self.history[self.cursor] != ordered:
            self.history = [*self.history[: self.cursor + 1], ordered][-100:]
            self.cursor = len(self.history) - 1

    def rebuild(self, row=0):
        self.refreshing = True
        self.listing.clear()
        for page in self.history[self.cursor]:
            self.listing.addItem(page_item(page, self))
        self.refresh_documents()
        self.refreshing = False
        count = self.listing.count()
        if count:
            self.listing.setCurrentRow(
                min(row, count - 1), QItemSelectionModel.SelectionFlag.NoUpdate
            )
        else:
            self.viewer.load(None, 0, 0)
        self.summarize()
        self.pages_changed.emit()

    def order_changed(self, *_):
        if not self.refreshing:
            self.remember(self.pages())
            self.refresh_documents()
            self.selected_page(self.listing.currentRow())

    def refresh_documents(self):
        self.documents.clear()
        if self.mode != TOOLS[0]:
            return
        pages = self.pages()
        counts = Counter(page.path for page in pages)
        documents = {}
        for page in pages:
            documents.setdefault(page.path, page)
        for reference in documents.values():
            item = QListWidgetItem(reference.path.name)
            try:
                size = f"{reference.path.stat().st_size / 1024:.0f} KB"
            except OSError:
                size = "size unavailable"
            item.setData(Qt.ItemDataRole.UserRole, reference)
            item.setData(Qt.ItemDataRole.UserRole + 1, size)
            self.translate_document(item, counts[reference.path])
            self.documents.addItem(item)

    def translate_document(self, item, count):
        reference = item.data(Qt.ItemDataRole.UserRole)
        size = tr(self, item.data(Qt.ItemDataRole.UserRole + 1))
        meta = tr(self, "{pages} pages · {size}", pages=count, size=size)
        hint = tr(self, "Double-click to jump to its first page.")
        item.setText(f"{reference.path.name}\n{meta}")
        item.setToolTip(f"{reference.path.name}\n{hint}")

    def retranslate(self):
        self.viewer.retranslate()
        counts = Counter(page.path for page in self.pages())
        for index in range(self.documents.count()):
            item = self.documents.item(index)
            self.translate_document(item, counts[item.data(Qt.ItemDataRole.UserRole).path])
        if self.mode != TOOLS[1]:
            for index in range(self.listing.count()):
                translate_page_item(self.listing.item(index), self)
        self.summarize()

    def reorder_documents(self):
        pages = self.pages()
        order = {
            self.documents.item(row).data(Qt.ItemDataRole.UserRole).path: row
            for row in range(self.documents.count())
        }
        self.remember(sorted(pages, key=lambda page: order[page.path]))
        self.rebuild()

    def locate_document(self, item):
        wanted = item.data(Qt.ItemDataRole.UserRole).path
        for index, page in enumerate(self.pages()):
            if page.path == wanted:
                self.listing.setCurrentRow(index)
                return

    def selected_page(self, row):
        if self.refreshing:
            return
        if row >= 0:
            self.viewer.load(
                self.listing.item(row).data(Qt.ItemDataRole.UserRole), row, self.listing.count()
            )
        self.summarize()

    def navigate(self, move):
        row = self.listing.currentRow() + move
        if 0 <= row < self.listing.count():
            self.listing.setCurrentRow(row)

    def undo(self):
        if self.cursor > 0:
            self.cursor -= 1
            self.rebuild()

    def redo(self):
        if self.cursor + 1 < len(self.history):
            self.cursor += 1
            self.rebuild()

    def duplicate(self):
        rows = self.selected()
        pages = self.pages()
        if rows:
            pages[rows[-1] + 1 : rows[-1] + 1] = [pages[row] for row in rows]
            self.remember(pages)
            self.rebuild(rows[-1] + 1)

    def remove(self):
        rows = set(self.selected())
        if rows:
            self.remember([page for row, page in enumerate(self.pages()) if row not in rows])
            self.rebuild(min(rows))

    def invert(self):
        for index in range(self.listing.count()):
            item = self.listing.item(index)
            item.setSelected(not item.isSelected())

    def move(self, delta):
        row = self.listing.currentRow()
        pages = self.pages()
        if row >= 0 and 0 <= row + delta < len(pages):
            pages.insert(row + delta, pages.pop(row))
            self.remember(pages)
            self.rebuild(row + delta)

    def rotate_pages(self, degrees):
        row = self.listing.currentRow()
        selected = self.selected() or ([row] if row >= 0 else [])
        pages = self.pages()
        for index in selected:
            page = pages[index]
            pages[index] = replace(page, rotation=(page.rotation + degrees) % 360)
        self.remember(pages)
        self.rebuild(row if row >= 0 else 0)
        for index in selected:
            self.listing.item(index).setSelected(True)

    def insert_blank(self):
        pages = self.pages()
        row = self.listing.currentRow() + 1
        pages.insert(row, BlankPage())
        self.remember(pages)
        self.rebuild(row)

    def reverse_order(self):
        pages = self.pages()
        self.remember(pages[::-1])
        self.rebuild()

    def add_boundary(self):
        row = self.listing.currentRow()
        if not 0 <= row < self.listing.count() - 1:
            self.failed.emit("Select a page before the last page to place a split after it.")
            return
        old = self.range.text() if self.groups.currentData() == "Boundaries" else ""
        self.groups.setCurrentText("Boundaries")
        try:
            values = set(page_range(old, self.listing.count() - 1)) if old else set()
        except ValueError as error:
            self.failed.emit(str(error))
            return
        values.symmetric_difference_update({row})
        self.range.setText(",".join(str(value + 1) for value in sorted(values)))

    def summarize(self, *_):
        if self.refreshing:
            return
        count = self.listing.count()
        selection = len(self.selected())
        split = self.mode == TOOLS[1]
        converting = self.mode == TOOLS[3]
        separate = self.mode == TOOLS[2] and self.action.currentIndex() == 3
        self.naming.setVisible(split or converting or separate)
        self.zip.setVisible(split or converting or separate)
        self.quality.setEnabled(self.fmt.currentData() == "JPEG")
        self.transparent.setEnabled(self.fmt.currentData() == "PNG")
        hint = (
            {
                "Every N pages": "Pages per file",
                "Custom ranges": "Groups such as 1-3;4-6;7",
                "Boundaries": "Split after pages such as 2,4",
            }.get(self.groups.currentData(), "All pages" if split else "Page range, e.g. 1–3,5")
            if split
            else "Page range, e.g. 1-3,5"
        )
        self.range.setPlaceholderText(tr(self, hint))
        documents = Counter(page.path for page in self.pages() if isinstance(page, Page))
        details = [
            tr(
                self,
                "{documents} PDF(s) · {pages} pages · {selection} selected",
                documents=len(documents),
                pages=count,
                selection=selection,
            )
        ]
        if self.mode == TOOLS[2] and self.action.currentIndex() == 1:
            details.append(tr(self, "{count} remaining", count=count - selection))
        if split and count:
            boundaries = set()
            try:
                groups = split_groups(self.groups.currentData(), self.range.text(), count)
                details.append(tr(self, "{count} output files", count=len(groups)))
                if self.groups.currentData() == "Boundaries":
                    boundaries = {group[-1] for group in groups[:-1]}
                if len(groups) <= 12:
                    details.append(
                        " / ".join(f"{group[0] + 1}–{group[-1] + 1}" for group in groups)
                    )
            except ValueError as error:
                details.append(tr(self, str(error)))
            for index in range(count):
                item = self.listing.item(index)
                marked = index in boundaries
                translate_page_item(item, self, split=marked)
                item.setBackground(QBrush(QColor("#567eb0")) if marked else QBrush())
        if converting and self.viewer.page and not self.viewer.image.pixmap().isNull():
            rect = self.viewer.scene.sceneRect()
            details.append(
                tr(
                    self,
                    "Preview ≈ {width} × {height} px",
                    width=round(rect.width() * self.dpi.value() / 72),
                    height=round(rect.height() * self.dpi.value() / 72),
                )
            )
        self.summary.setText(" · ".join(details))
        self.export_button.setEnabled(bool(count))

    def output_plan(self):
        pages = self.pages()
        chosen = self.selected()
        if not pages:
            raise ValueError("Add a PDF first.")
        mode = self.mode
        multi = mode in {TOOLS[1], TOOLS[3]}
        groups = [pages]
        if mode == TOOLS[1]:
            groups = [
                [pages[i] for i in group]
                for group in split_groups(self.groups.currentData(), self.range.text(), len(pages))
            ]
        if mode == TOOLS[2]:
            action = self.action.currentIndex()
            if action and not chosen:
                raise ValueError("Select one or more pages.")
            if action == 1:
                groups = [[page for index, page in enumerate(pages) if index not in set(chosen)]]
            elif action == 2:
                groups = [[pages[index] for index in chosen]]
            elif action == 3:
                multi = True
                groups = [[pages[index]] for index in chosen]
        if mode == TOOLS[3]:
            raw = self.range.text().strip()
            indexes = page_range(raw, len(pages)) if raw else chosen or list(range(len(pages)))
            groups = [[pages[index]] for index in indexes]
        if not groups[0]:
            raise ValueError("The output must contain at least one page.")
        return multi, groups

    def create_job(self, target: Path, multi, groups):
        prefix = self.naming.text().strip() or "PDF Toolbox"
        mode = self.mode
        archive = self.zip.isChecked()
        fmt = self.fmt.currentData()
        quality, dpi, transparency = (
            self.quality.value(),
            self.dpi.value(),
            self.transparent.isChecked(),
        )
        extension = ("jpg" if fmt == "JPEG" else "png") if mode == TOOLS[3] else "pdf"

        def work(cancelled, progress):
            if not multi:
                return [export(groups[0], target, cancelled=cancelled, progress=progress)]
            stems = [
                prefix.replace("{n}", f"{i:03d}") if "{n}" in prefix else f"{prefix}-{i:03d}"
                for i in range(1, len(groups) + 1)
            ]
            names = [f"{stem}.{extension}" for stem in stems]

            def produce(index, path):
                if mode == TOOLS[3]:
                    path.write_bytes(convert(groups[index][0], fmt, dpi, quality, transparency))
                else:
                    write_pdf(groups[index], path, cancelled)
                progress(index + 1, len(groups))

            zip_name = prefix.replace("{n}", "pages").strip() + ".zip" if archive else None
            return publish(target, names, produce, cancelled, zip_name)

        return work
