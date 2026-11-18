"""Batch PDF-to-Word panel, using the application's existing Qt workers."""

import io
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, QRect, QRectF, QSize, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QCursor, QDesktopServices, QIcon, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStyle,
    QStyleOptionButton,
    QStyleOptionViewItem,
    QStylePainter,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)

from .appearance import ThemedComboBox, action_button, tool_icon
from .pdf import Cancelled, Page, check_cancelled, render, safe_local
from .viewer import local_paths
from .word_com import inspect_word
from .word_conversion import generate, pdf_inputs
from .word_layout import Layout, MM, PlacementSettings, fit_image, natural_key
from .word_logging import record_error

WORD_TOOL = "PDF to Word"
FILE_METADATA = Qt.ItemDataRole.UserRole + 1


def grip_rect(row: QRect) -> QRect:
    return QRect(row.left() + 4, row.top() + 3, 27, row.height() - 6)


class FileCard(QStyledItemDelegate):
    def paint(self, painter, option, index):
        card = QStyleOptionViewItem(option)
        self.initStyleOption(card, index)
        palette = self.parent().window().theme_palette
        metadata = index.data(FILE_METADATA) or ""
        name = card.text.removesuffix(metadata)
        style = card.widget.style() if card.widget else QApplication.style()
        text_area = style.subElementRect(QStyle.SubElement.SE_ItemViewItemText, card, card.widget)
        card.text = ""
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, card, painter, card.widget)

        center = grip_rect(option.rect).center()
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette["ink"]))
        for x in (-3, 3):
            for y in (-6, 0, 6):
                painter.drawEllipse(QRectF(center.x() + x - 1.4, center.y() + y - 1.4, 2.8, 2.8))
        painter.setClipRect(text_area)
        painter.setFont(card.font)
        metrics = card.fontMetrics
        metadata = metrics.elidedText(metadata, Qt.TextElideMode.ElideRight, text_area.width())
        filename = metrics.elidedText(
            name,
            Qt.TextElideMode.ElideMiddle,
            max(0, text_area.width() - metrics.horizontalAdvance(metadata)),
        )
        position = QPointF(
            text_area.left(), text_area.center().y() + (metrics.ascent() - metrics.descent()) / 2
        )
        painter.setPen(QColor(palette["ink"]))
        painter.drawText(position, filename)
        painter.setPen(QColor(palette["file_metadata"]))
        painter.drawText(position + QPointF(metrics.horizontalAdvance(filename), 0), metadata)
        painter.restore()


class FileList(QListWidget):
    files = Signal(list)
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("WordFiles")
        self.setItemDelegate(FileCard(self))
        self.setMouseTracking(True)
        self.handle_pressed = False
        self.dragging = False
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.model().rowsMoved.connect(lambda *_: self.changed.emit())
        self.setAccessibleName("PDF files in insertion order. Drag to reorder.")
        self.setFixedHeight(154)

    def over_handle(self, point):
        item = self.itemAt(point)
        return item is not None and grip_rect(self.visualItemRect(item)).contains(point)

    def update_cursor(self, point):
        if self.dragging:
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        elif self.over_handle(point):
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.viewport().unsetCursor()

    def viewportEvent(self, event):
        if event.type() == QEvent.Type.Leave and not self.dragging:
            self.viewport().unsetCursor()
        return super().viewportEvent(event)

    def mousePressEvent(self, event):
        self.handle_pressed = event.button() == Qt.MouseButton.LeftButton and self.over_handle(
            event.position().toPoint()
        )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.update_cursor(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.handle_pressed = False
        super().mouseReleaseEvent(event)

    def startDrag(self, supported_actions):
        if not self.handle_pressed:
            return
        self.dragging = True
        self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        try:
            super().startDrag(supported_actions)
        finally:
            QApplication.restoreOverrideCursor()
            self.dragging = self.handle_pressed = False
            self.update_cursor(self.viewport().mapFromGlobal(QCursor.pos()))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            self.files.emit(local_paths(event.mimeData()))
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dropEvent(event)
            self.changed.emit()


class WordDropField(QFrame):
    files = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("ToolDropArea")
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.highlight(True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.highlight(False)
        event.accept()

    def dropEvent(self, event):
        self.highlight(False)
        self.files.emit(local_paths(event.mimeData()))
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def highlight(self, active):
        self.setProperty("dragging", active)
        self.style().unpolish(self)
        self.style().polish(self)


class WordDrop(QPushButton):
    files = Signal(list)

    def __init__(self, label="Change Word template…"):
        super().__init__(label)
        self.setObjectName("WordTemplateDrop")
        self.setProperty("iconKind", "paper")
        self.setMinimumHeight(140)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        self.icon_label = QLabel()
        self.icon_label.setObjectName("WordTemplateIcon")
        self.icon_label.setFixedSize(44, 44)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label = QLabel()
        self.name_label.setObjectName("WordTemplateName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.hint_label = QLabel()
        self.hint_label.setObjectName("WordTemplateHint")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setWordWrap(True)
        for widget in (self.icon_label, self.name_label, self.hint_label):
            widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.setText(label)
        self.setToolTip("Drop a Word template here, or click to browse.")
        self.setAccessibleName("Word template. Drop a file here or click to change it.")
        self.setAcceptDrops(True)

    def setText(self, text):
        super().setText(text)
        if hasattr(self, "name_label"):
            name, separator, hint = text.partition("\n")
            self.name_label.setText(name if separator else "Word template")
            self.hint_label.setText(hint if separator else name)

    def setIcon(self, icon):
        super().setIcon(icon)
        if hasattr(self, "icon_label"):
            self.icon_label.setPixmap(icon.pixmap(24, 24))

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        option.icon = QIcon()
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.files.emit(local_paths(event.mimeData()))
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()


class LayoutPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.layout_info = Layout(595, 842, 72, 72, 523, 770)
        self.settings = PlacementSettings()
        self.picture = QImage()
        self.header = QImage()
        self.footer = QImage()
        self.setMinimumSize(220, 280)
        self.setAccessibleName("Schematic Word page, header, footer, margins and safe image area")

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        layout = self.layout_info
        scale = min((self.width() - 24) / layout.width, (self.height() - 20) / layout.height)
        page_x = (self.width() - layout.width * scale) / 2
        page_y = (self.height() - layout.height * scale) / 2
        painter.translate(page_x, page_y)
        painter.scale(scale, scale)
        painter.fillRect(QRectF(0, 0, layout.width, layout.height), QColor("white"))
        painter.setPen(QPen(QColor("#596675"), 1 / scale))
        painter.drawRect(QRectF(0, 0, layout.width, layout.height))
        for image, top, bottom in (
            (self.header, 0, layout.top),
            (self.footer, layout.bottom, layout.height),
        ):
            band = QRectF(0, top, layout.width, bottom - top)
            if not image.isNull():
                painter.drawImage(band, image)
            else:
                painter.fillRect(band, QColor("#e9d9d2"))
        margin = self.settings.safety_mm * MM
        safe = QRectF(
            layout.left + margin,
            layout.top + margin,
            layout.right - layout.left - 2 * margin,
            layout.bottom - layout.top - 2 * margin,
        )
        painter.setPen(QPen(QColor("#4c8b72"), 1 / scale, Qt.PenStyle.DashLine))
        painter.drawRect(safe)
        if not self.picture.isNull():
            try:
                rect = fit_image(layout, self.picture.width(), self.picture.height(), self.settings)
            except ValueError:
                pass
            else:
                painter.drawImage(QRectF(rect.x, rect.y, rect.width, rect.height), self.picture)


class WordPanel(QScrollArea):
    detailed_progress = Signal(object)

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.info = None
        self.cursor = 0
        self.preview_token = 0
        self.output_path = None
        self.setWidgetResizable(True)
        self.setObjectName("WordPanel")
        self.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setObjectName("WordPanelBody")
        self.setWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 10, 18, 12)
        self.intake = QWidget()
        root.addWidget(self.intake, 1)
        intake = QVBoxLayout(self.intake)
        intake.setSpacing(12)
        intake.addStretch(2)
        center = Qt.AlignmentFlag.AlignHCenter
        icon = QLabel()
        icon.setObjectName("EmptyToolIcon")
        icon.setProperty("tone", "lilac")
        icon.setFixedSize(80, 80)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(tool_icon("paper", "#733d74", 40).pixmap(40, 40))
        intake.addWidget(icon, alignment=center)
        heading = QLabel(WORD_TOOL)
        heading.setObjectName("EmptyToolTitle")
        intake.addWidget(heading, alignment=center)
        hint = QLabel("Add PDF pages to a copy of your Word template.")
        hint.setObjectName("HeroHint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        intake.addWidget(hint)
        fields = QHBoxLayout()
        fields.setSpacing(14)
        intake.addLayout(fields)
        for title, instruction, button_text, browse, receive in (
            (
                "PDF files",
                "Drop one or more PDF files here",
                "Browse PDFs…",
                self.browse_pdfs,
                self.add_files,
            ),
            (
                "Word template",
                "Drop an existing .docx here",
                "Browse Word files…",
                self.browse_word,
                self.select_word,
            ),
        ):
            field = WordDropField()
            field.files.connect(receive)
            column = QVBoxLayout(field)
            column.setContentsMargins(14, 18, 14, 18)
            label = QLabel(title)
            label.setObjectName("ToolTitle")
            column.addWidget(label, alignment=center)
            state = QLabel(instruction)
            state.setWordWrap(True)
            state.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(state)
            button = action_button("folder", button_text)
            button.clicked.connect(browse)
            column.addWidget(button, alignment=center)
            fields.addWidget(field, 1)
            if title == "PDF files":
                self.pdf_intake_state = state
                self.clear_pending_pdfs = QPushButton("Clear selection")
                self.clear_pending_pdfs.clicked.connect(self.clear)
                column.addWidget(self.clear_pending_pdfs, alignment=center)
            else:
                self.word_intake_state = state
        intake.addStretch(3)
        self.details = QWidget()
        root.addWidget(self.details, 1)
        main = QVBoxLayout(self.details)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(8)
        columns = QHBoxLayout()
        columns.setSpacing(16)
        main.addLayout(columns)
        controls = QVBoxLayout()
        controls.setSpacing(7)
        columns.addLayout(controls, 3)
        insertion = QLabel("PDF insertion")
        insertion.setObjectName("WordSection")
        controls.addWidget(insertion)
        self.files = FileList()
        self.files.files.connect(self.add_files)
        self.files.changed.connect(self.refresh)
        controls.addWidget(self.files)
        row = QHBoxLayout()
        controls.addLayout(row)
        for icon, label, callback in [
            ("folder", "Add PDFs…", self.browse_pdfs),
            ("delete", "Remove", self.remove),
            ("close", "Clear", self.clear),
            ("organize", "Natural sort", self.sort_files),
        ]:
            button = action_button(icon, label)
            button.clicked.connect(callback)
            row.addWidget(button)
        template_title = QLabel("Word template")
        template_title.setObjectName("WordSection")
        controls.addWidget(template_title)
        self.word_drop = WordDrop()
        self.word_drop.clicked.connect(self.browse_word)
        self.word_drop.files.connect(self.select_word)
        controls.addWidget(self.word_drop)
        self.word_info = QLabel()
        self.word_info.setWordWrap(True)
        controls.addWidget(self.word_info)
        form = QFormLayout()
        controls.addLayout(form)
        self.horizontal = ThemedComboBox()
        self.horizontal.addItems(["Left", "Center", "Right"])
        self.horizontal.setCurrentText("Center")
        self.vertical = ThemedComboBox()
        self.vertical.addItems(["Top", "Center", "Bottom"])
        placement = PlacementSettings()
        self.horizontal.setCurrentText(placement.horizontal)
        self.vertical.setCurrentText(placement.vertical)
        form.addRow("Horizontal alignment", self.horizontal)
        form.addRow("Vertical alignment", self.vertical)
        advanced = action_button("settings", "Show advanced settings")
        advanced.setCheckable(True)
        self.advanced_body = QWidget()
        advanced_form = QFormLayout(self.advanced_body)
        advanced_form.setContentsMargins(0, 0, 0, 0)
        self.dpi = ThemedComboBox()
        self.dpi.addItems(["150", "200", "300", "600"])
        self.dpi.setCurrentText("300")
        self.format = ThemedComboBox()
        self.format.addItems(["JPEG", "PNG"])
        self.quality = QSpinBox()
        self.quality.setRange(1, 100)
        self.quality.setValue(95)
        self.scale = QSpinBox()
        self.scale.setRange(1, 200)
        self.scale.setValue(100)
        self.scale.setSuffix("% (capped to fit)")
        self.margin = QDoubleSpinBox()
        self.margin.setRange(0, 50)
        self.margin.setValue(5)
        self.margin.setSuffix(" mm")
        for label, field in [
            ("Resolution (DPI)", self.dpi),
            ("Image format", self.format),
            ("JPEG quality", self.quality),
            ("Image scale", self.scale),
            ("Extra safety margin", self.margin),
        ]:
            advanced_form.addRow(label, field)
        self.advanced_body.hide()
        advanced.toggled.connect(self.advanced_body.setVisible)
        advanced.toggled.connect(
            lambda opened: advanced.setText(
                "Hide advanced settings" if opened else "Show advanced settings"
            )
        )
        controls.addWidget(advanced)
        controls.addWidget(self.advanced_body)
        output_title = QLabel("Output location")
        output_title.setObjectName("WordSection")
        controls.addWidget(output_title)
        self.folder = QLineEdit()
        self.folder.setAccessibleName("Output directory")
        self.filename = QLineEdit()
        self.filename.setAccessibleName("Output filename")
        output_row = QHBoxLayout()
        output_row.addWidget(self.folder, 1)
        choose_folder = action_button("folder", "Folder…")
        choose_folder.clicked.connect(self.browse_folder)
        output_row.addWidget(choose_folder)
        controls.addLayout(output_row)
        controls.addWidget(self.filename)
        self.generate_button = action_button("paper", "Generate Word Document", primary=True)
        self.generate_button.setObjectName("BrowsePrimary")
        self.generate_button.clicked.connect(self.start)
        controls.addWidget(self.generate_button)
        controls.addStretch()
        divider = QFrame()
        divider.setObjectName("Divider")
        divider.setFixedWidth(1)
        columns.addWidget(divider)
        right = QVBoxLayout()
        right.setSpacing(7)
        columns.addLayout(right, 2)
        preview_title = QLabel("Schematic preview")
        preview_title.setObjectName("DetailHeading")
        preview_title.setToolTip(
            "Word renders the header and footer. The green outline marks the image's safe area."
        )
        right.addWidget(preview_title)
        self.preview = LayoutPreview()
        right.addWidget(self.preview, 1)
        self.page_caption = QLabel("Add PDFs to preview")
        self.page_caption.setWordWrap(True)
        right.addWidget(self.page_caption)
        navigation = QHBoxLayout()
        for icon, label, delta in [("previous", "Previous", -1), ("next", "Next", 1)]:
            button = action_button(icon, label)
            button.clicked.connect(lambda _, d=delta: self.navigate(d))
            navigation.addWidget(button)
        right.addLayout(navigation)
        self.status = QLabel()
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        for combo in (self.horizontal, self.vertical, self.dpi, self.format):
            combo.currentTextChanged.connect(self.update_placement)
        for spin in (self.quality, self.scale, self.margin):
            spin.valueChanged.connect(self.update_placement)
        self.detailed_progress.connect(self.report)
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh()

    def settings(self):
        return PlacementSettings(
            self.horizontal.currentText(),
            self.vertical.currentText(),
            self.scale.value(),
            self.margin.value(),
            int(self.dpi.currentText()),
            self.format.currentText(),
            self.quality.value(),
        )

    def inputs(self):
        return [
            self.files.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.files.count())
        ]

    def browse_pdfs(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Add PDFs", "", "PDF files (*.pdf)")
        if paths:
            self.add_files([Path(path) for path in paths])

    def add_files(self, paths):
        if self.owner.busy:
            return
        existing = {item.path for item in self.inputs()}
        paths = [Path(path) for path in paths]

        def work(cancel, _):
            accepted, warnings = [], []
            for path in paths:
                if cancel.is_set():
                    raise Cancelled()
                if path.resolve() in existing:
                    warnings.append(f"Duplicate PDF: {path.name}")
                    continue
                try:
                    item = pdf_inputs([path])[0]
                except ValueError as error:
                    warnings.append(str(error))
                else:
                    accepted.append(item)
                    existing.add(item.path)
            return accepted, warnings

        def done(result, error):
            if error:
                if not isinstance(error, Cancelled):
                    self.owner.alert(str(error))
                return
            accepted, warnings = result
            for item in accepted:
                row = QListWidgetItem()
                row.setSizeHint(QSize(0, 38))
                row.setData(Qt.ItemDataRole.UserRole, item)
                row.setToolTip(str(item.path))
                self.files.addItem(row)
            self.refresh()
            if warnings:
                self.owner.alert("\n".join(warnings))

        self.owner.run_job(work, "Validating PDF files…", done)

    def browse_word(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select existing Word document", "", "Word documents (*.docx)"
        )
        if path:
            self.select_word([Path(path)])

    def select_word(self, paths):
        if self.owner.busy:
            return
        if len(paths) != 1:
            self.owner.alert("Choose one existing .docx document.")
            return
        path = Path(paths[0])

        def done(info, error):
            if error:
                if not isinstance(error, Cancelled):
                    self.owner.alert(str(error))
            else:
                self.info = info
                self.folder.setText(str(path.parent))
                self.filename.setText(path.stem + "_with_images.docx")
                self.preview.layout_info = info.layout
            self.refresh()

        def work(cancel, _):
            check_cancelled(cancel)
            info = inspect_word(path)
            check_cancelled(cancel)
            return info

        self.owner.run_job(work, "Inspecting Word layout…", done)

    def remove(self):
        for item in self.files.selectedItems():
            self.files.takeItem(self.files.row(item))
        self.refresh()

    def clear(self):
        self.files.clear()
        self.cursor = 0
        self.refresh()

    def sort_files(self):
        rows = [self.files.takeItem(0) for _ in range(self.files.count())]
        for row in sorted(
            rows, key=lambda item: natural_key(item.data(Qt.ItemDataRole.UserRole).path.name)
        ):
            self.files.addItem(row)
        self.refresh()

    def refresh(self):
        inputs = self.inputs()
        total = sum(item.pages for item in inputs)
        ready = bool(inputs and self.info)
        self.intake.setVisible(not ready)
        self.details.setVisible(ready)
        self.clear_pending_pdfs.setVisible(bool(inputs))
        self.pdf_intake_state.setText(
            f"{len(inputs)} selected · {total} pages"
            if inputs
            else "Drop one or more PDF files here"
        )
        self.word_intake_state.setText(
            self.info.path.name if self.info else "Drop an existing .docx here"
        )
        for index, item in enumerate(inputs):
            unit = "page" if item.pages == 1 else "pages"
            metadata = f" ({item.pages} {unit} · {item.size / 1024:,.0f} KB)"
            row = self.files.item(index)
            row.setData(FILE_METADATA, metadata)
            row.setText(f"{index + 1}.  {item.path.name}{metadata}")
        self.generate_button.setEnabled(ready)
        if self.info:
            info, layout = self.info, self.info.layout
            self.preview.layout_info = layout
            orientation = "Landscape" if layout.width > layout.height else "Portrait"
            self.word_drop.setText(info.path.name + "\nDrop another file or click to change")
            self.word_info.setText(f"Total pages after insertion: {info.pages + total}")
            self.word_info.setToolTip(
                f"{info.pages} original pages · {info.size / 1024:,.0f} KB\n"
                f"{layout.width / MM:.1f} × {layout.height / MM:.1f} mm · {orientation}"
            )
        self.cursor = max(0, min(self.cursor, total - 1))
        if ready:
            self.load_preview()
        else:
            self.preview_token += 1

    def navigate(self, delta):
        total = sum(item.pages for item in self.inputs())
        self.cursor = max(0, min(self.cursor + delta, total - 1))
        self.load_preview()

    def update_placement(self, *_):
        self.preview.settings = self.settings()
        self.preview.update()

    def load_preview(self):
        self.preview_token += 1
        token = self.preview_token
        index = self.cursor
        bands = self.info.preview_bands if self.info else ()
        self.preview.header = QImage()
        self.preview.footer = QImage()
        hint = "Word header and footer preview unavailable"
        if bands:
            # After the first appended page, odd/even header and footer variants repeat.
            sample = index if index < len(bands) else 1 + (index - 1) % 2
            header, footer = bands[sample]
            self.preview.header = QImage.fromData(header)
            self.preview.footer = QImage.fromData(footer)
            hint = "Sample page fields may differ in the saved document"
        self.preview.setToolTip(hint)
        for item in self.inputs():
            if index < item.pages:
                reference = Page(item.path, index)
                break
            index -= item.pages
        else:
            self.preview.picture = QImage()
            self.page_caption.setText("Add PDFs to preview")
            self.preview.update()
            return
        prefix = (
            f"Output page {self.info.pages + self.cursor + 1}"
            if self.info
            else "Select Word for page count"
        )
        if not bands:
            prefix += f"\n{hint}"
        self.page_caption.setText(f"{reference.path.name} · PDF page {index + 1}\n{prefix}")

        def work(cancel, _):
            with render(reference, pixels=700) as image:
                buffer = io.BytesIO()
                image.save(buffer, "PNG")
                return buffer.getvalue()

        def done(data, error):
            if token != self.preview_token:
                return
            self.preview.picture = QImage.fromData(data) if not error else QImage()
            if error:
                self.owner.alert(
                    "The preview could not open this page. Check that the PDF still opens."
                )
            self.preview.update()

        self.owner.thumbs.submit(work, done)

    def browse_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Output folder", self.folder.text())
        if path:
            self.folder.setText(path)

    def start(self):
        if not self.info or self.owner.busy:
            return
        filename = self.filename.text().strip()
        if Path(filename).name != filename or not filename.lower().endswith(".docx"):
            self.owner.alert("Enter a filename ending in .docx, without a folder path.")
            return
        if not self.folder.text().strip() or not Path(self.folder.text()).is_dir():
            self.owner.alert("Choose an existing local output folder.")
            return
        output = Path(self.folder.text()) / filename
        if output.resolve() == self.info.path.resolve():
            self.owner.alert("Choose a different output filename. The original is preserved.")
            return
        if not safe_local(output):
            self.owner.alert("Choose a local output folder.")
            return
        overwrite = False
        if output.exists():
            box = self.owner.mascot_message(
                QMessageBox.Icon.Question,
                "Output already exists",
                "Overwrite this output or use a new filename?",
            )
            replace = box.addButton("Overwrite output", QMessageBox.ButtonRole.DestructiveRole)
            unique = box.addButton("Use new filename", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            clicked = box.clickedButton()
            box.deleteLater()
            if clicked is unique:
                number = 2
                while output.exists():
                    output = output.with_name(f"{Path(filename).stem}_{number}.docx")
                    number += 1
                self.filename.setText(output.name)
            elif clicked is replace:
                overwrite = True
            else:
                return
        inputs, source, settings = self.inputs(), self.info.path, self.settings()
        self.status.clear()

        def work(cancel, progress):
            def report(value):
                self.detailed_progress.emit(value)
                progress(value.processed * 99, value.total * 100)

            return generate(inputs, source, output, settings, cancel, report, overwrite=overwrite)

        def done(result, error):
            if error:
                if not isinstance(error, Cancelled):
                    record_error("Word generation", error)
                    self.owner.alert(str(error))
                    self.status.clear()
                else:
                    self.status.setText("Cancelled. No output was saved.")
                return
            self.output_path = result.path
            self.show_result(result.added_pages, result.final_pages)

        self.owner.run_job(work, "Generating Word document…", done, show_details=True)

    def show_result(self, added_pages, final_pages):
        dialog = QDialog(self.owner)
        dialog.setWindowTitle("Word document saved")
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.setMinimumWidth(340)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)
        title = QLabel("Word document saved")
        title.setObjectName("Section")
        header = QHBoxLayout()
        mascot = QLabel()
        mascot.setPixmap(
            self.owner.drop.mascot.pixmap.scaled(
                60,
                60,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        header.addWidget(mascot)
        message = QVBoxLayout()
        message.addWidget(title)
        message.addWidget(QLabel(f"Pages added: {added_pages} · Total pages: {final_pages}"))
        header.addLayout(message, 1)
        layout.addLayout(header)
        for icon, label, callback, primary in (
            ("paper", "Open Word Document", self.open_output, True),
            ("folder", "Open Output Folder", self.open_folder, False),
            ("blank", "Start New Conversion", self.reset, False),
        ):
            button = action_button(icon, label, primary=primary)
            ink = "on_primary" if primary else "primary"
            button.setIcon(tool_icon(icon, self.owner.theme_palette[ink]))
            button.clicked.connect(dialog.accept)
            button.clicked.connect(callback)
            layout.addWidget(button)
            if primary:
                button.setDefault(True)
                button.setFocus()
        dialog.open()

    def report(self, value):
        remaining = (
            (value.total - value.processed) * value.elapsed / value.processed
            if value.processed
            else None
        )
        lines = [value.stage]
        if value.filename:
            lines.append(f"{value.filename} · PDF page {value.page}/{value.file_pages}")
        lines.append(f"Pages added: {value.processed}/{value.total}")
        elapsed = f"Elapsed: {value.elapsed:.0f}s"
        if remaining is not None and remaining > 0:
            elapsed += f" · Estimated remaining: {remaining:.0f}s"
        lines.append(elapsed)
        if self.owner.processing:
            self.owner.processing.details.setText("\n".join(lines))

    def open_output(self):
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))

    def open_folder(self):
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path.parent)))

    def reset(self):
        self.info = None
        self.word_drop.setText("Drop a Word template here or click to browse")
        self.clear()
        self.word_info.setText("Select an existing Word document.")
        self.status.clear()
