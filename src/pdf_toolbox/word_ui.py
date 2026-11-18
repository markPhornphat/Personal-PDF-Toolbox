"""Batch PDF-to-Word panel, using the application's existing Qt workers."""

import io
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .pdf import Cancelled, Page, check_cancelled, render, safe_local
from .viewer import local_paths
from .word_com import inspect_word
from .word_conversion import generate, pdf_inputs
from .word_layout import Layout, MM, PlacementSettings, fit_image, natural_key
from .word_logging import record_error

WORD_TOOL = "PDF to Word"


class FileList(QListWidget):
    files = Signal(list)
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.model().rowsMoved.connect(lambda *_: self.changed.emit())
        self.setAccessibleName("PDF files in insertion order. Drag to reorder.")
        self.setMinimumHeight(130)

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
            event.acceptProposedAction()
        else:
            super().dropEvent(event)


class WordDrop(QPushButton):
    files = Signal(list)

    def __init__(self):
        super().__init__("Drop an existing .docx here, or browse…")
        self.setAcceptDrops(True)
        self.setMinimumHeight(55)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.files.emit(local_paths(event.mimeData()))
        event.acceptProposedAction()


class LayoutPreview(QWidget):
    def __init__(self):
        super().__init__()
        self.layout_info = Layout(595, 842, 72, 72, 523, 770)
        self.settings = PlacementSettings()
        self.picture = QImage()
        self.setMinimumSize(220, 280)
        self.setAccessibleName("Schematic Word page, header, footer, margins and safe image area")

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout = self.layout_info
        scale = min((self.width() - 24) / layout.width, (self.height() - 20) / layout.height)
        painter.translate((self.width() - layout.width * scale) / 2, 10)
        painter.scale(scale, scale)
        painter.fillRect(QRectF(0, 0, layout.width, layout.height), QColor("white"))
        painter.setPen(QPen(QColor("#596675"), 1 / scale))
        painter.drawRect(QRectF(0, 0, layout.width, layout.height))
        painter.fillRect(QRectF(0, 0, layout.width, layout.top), QColor("#e9d9d2"))
        painter.fillRect(
            QRectF(0, layout.bottom, layout.width, layout.height - layout.bottom), QColor("#e9d9d2")
        )
        painter.setPen(QColor("#313d48"))
        painter.drawText(
            QRectF(0, 0, layout.width, layout.top),
            Qt.AlignmentFlag.AlignCenter,
            "Header / protected area",
        )
        painter.drawText(
            QRectF(0, layout.bottom, layout.width, layout.height - layout.bottom),
            Qt.AlignmentFlag.AlignCenter,
            "Footer / protected area",
        )
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
                return
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
        content = QWidget()
        self.setWidget(content)
        main = QVBoxLayout(content)
        title = QLabel("PDF to Word")
        title.setObjectName("HeroTitle")
        main.addWidget(title)
        main.addWidget(
            QLabel("Append one PDF page image per new Word page. Everything stays local.")
        )
        columns = QHBoxLayout()
        main.addLayout(columns)
        controls = QVBoxLayout()
        columns.addLayout(controls, 3)
        controls.addWidget(QLabel("1. Add PDFs — drag rows to set the insertion order"))
        self.files = FileList()
        self.files.files.connect(self.add_files)
        self.files.changed.connect(self.refresh)
        controls.addWidget(self.files)
        row = QHBoxLayout()
        controls.addLayout(row)
        for label, callback in [
            ("Add PDFs…", self.browse_pdfs),
            ("Remove", self.remove),
            ("Clear", self.clear),
            ("Natural sort", self.sort_files),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.summary = QLabel("No PDFs selected")
        self.summary.setWordWrap(True)
        controls.addWidget(self.summary)
        controls.addWidget(QLabel("2. Select the existing Word document"))
        self.word_drop = WordDrop()
        self.word_drop.clicked.connect(self.browse_word)
        self.word_drop.files.connect(self.select_word)
        controls.addWidget(self.word_drop)
        self.word_info = QLabel("Requires Microsoft Word Desktop. Your original is preserved.")
        self.word_info.setWordWrap(True)
        controls.addWidget(self.word_info)
        form = QFormLayout()
        controls.addLayout(form)
        self.horizontal = QComboBox()
        self.horizontal.addItems(["Left", "Center", "Right"])
        self.horizontal.setCurrentText("Center")
        self.vertical = QComboBox()
        self.vertical.addItems(["Top", "Center", "Bottom"])
        self.vertical.setCurrentText("Bottom")
        form.addRow("Horizontal alignment", self.horizontal)
        form.addRow("Vertical alignment", self.vertical)
        controls.addWidget(
            QLabel("Append at end · 1 image per page · aspect ratio and protection always on")
        )
        advanced = QGroupBox("Advanced settings")
        advanced.setCheckable(True)
        advanced.setChecked(False)
        self.advanced_body = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.addWidget(self.advanced_body)
        advanced_form = QFormLayout(self.advanced_body)
        self.dpi = QComboBox()
        self.dpi.addItems(["150", "200", "300", "600"])
        self.dpi.setCurrentText("300")
        self.format = QComboBox()
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
        controls.addWidget(advanced)
        controls.addWidget(QLabel("3. Choose the output location"))
        self.folder = QLineEdit()
        self.folder.setAccessibleName("Output directory")
        self.filename = QLineEdit()
        self.filename.setAccessibleName("Output filename")
        output_row = QHBoxLayout()
        output_row.addWidget(self.folder, 1)
        choose_folder = QPushButton("Folder…")
        choose_folder.clicked.connect(self.browse_folder)
        output_row.addWidget(choose_folder)
        controls.addLayout(output_row)
        controls.addWidget(self.filename)
        self.generate_button = QPushButton("Generate Word Document")
        self.generate_button.setObjectName("BrowsePrimary")
        self.generate_button.clicked.connect(self.start)
        controls.addWidget(self.generate_button)
        right = QVBoxLayout()
        columns.addLayout(right, 2)
        caption = QLabel(
            "Schematic preview — not a Word rendering\nGreen: safe area · shaded: protected margins"
        )
        caption.setWordWrap(True)
        right.addWidget(caption)
        self.preview = LayoutPreview()
        right.addWidget(self.preview, 1)
        self.page_caption = QLabel("Add PDFs to preview")
        self.page_caption.setWordWrap(True)
        right.addWidget(self.page_caption)
        navigation = QHBoxLayout()
        for label, delta in [("Previous", -1), ("Next", 1)]:
            button = QPushButton(label)
            button.clicked.connect(lambda _, d=delta: self.navigate(d))
            navigation.addWidget(button)
        right.addLayout(navigation)
        self.status = QLabel()
        self.status.setWordWrap(True)
        main.addWidget(self.status)
        self.result_actions = QWidget()
        actions = QHBoxLayout(self.result_actions)
        for label, callback in [
            ("Open Word Document", self.open_output),
            ("Open Output Folder", self.open_folder),
            ("Start New Conversion", self.reset),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        main.addWidget(self.result_actions)
        self.result_actions.hide()
        for combo in (self.horizontal, self.vertical, self.dpi, self.format):
            combo.currentTextChanged.connect(self.update_placement)
        for spin in (self.quality, self.scale, self.margin):
            spin.valueChanged.connect(self.update_placement)
        self.detailed_progress.connect(self.report)
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
                self.status.setText(str(error) or "Cancelled")
                return
            accepted, warnings = result
            for item in accepted:
                row = QListWidgetItem(
                    f"{item.path.name}  ·  {item.pages} pages  ·  {item.size / 1024:,.0f} KB"
                )
                row.setData(Qt.ItemDataRole.UserRole, item)
                row.setToolTip(str(item.path))
                self.files.addItem(row)
            self.status.setText("\n".join(warnings))
            self.refresh()

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
            self.status.setText("Choose one existing .docx document.")
            return
        path = Path(paths[0])
        self.info = None
        self.refresh()

        def done(info, error):
            if error:
                self.word_info.setText(str(error))
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
        self.summary.setText(
            f"{len(inputs)} PDF files · {total} PDF pages · {total} images · "
            f"{total} additional Word pages"
        )
        self.generate_button.setEnabled(bool(inputs and self.info))
        if self.info:
            info, layout = self.info, self.info.layout
            orientation = "Landscape" if layout.width > layout.height else "Portrait"
            self.word_info.setText(
                f"{info.path.name} · {info.size / 1024:,.0f} KB · "
                f"{info.pages} pages\n{layout.width / MM:.1f} × "
                f"{layout.height / MM:.1f} mm · {orientation}\n"
                f"Expected final page count: {info.pages + total}"
            )
        self.cursor = max(0, min(self.cursor, total - 1))
        self.load_preview()

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
            f"Expected output page {self.info.pages + self.cursor + 1}"
            if self.info
            else "Select Word for page count"
        )
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
                self.status.setText("Preview could not be rendered. Check the selected PDF.")
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
            self.status.setText("Enter a filename ending in .docx, without a folder path.")
            return
        if not self.folder.text().strip() or not Path(self.folder.text()).is_dir():
            self.status.setText("Choose an existing local output folder.")
            return
        output = Path(self.folder.text()) / filename
        if output.resolve() == self.info.path.resolve():
            self.status.setText("Choose a different output filename. The original is preserved.")
            return
        if not safe_local(output):
            self.status.setText("Choose a local output folder.")
            return
        overwrite = False
        if output.exists():
            box = QMessageBox(
                QMessageBox.Icon.Question,
                "Output already exists",
                "Overwrite this output or use a new filename?",
                parent=self,
            )
            replace = box.addButton("Overwrite output", QMessageBox.ButtonRole.DestructiveRole)
            unique = box.addButton("Use new filename", QMessageBox.ButtonRole.AcceptRole)
            box.addButton(QMessageBox.StandardButton.Cancel)
            box.exec()
            if box.clickedButton() is unique:
                number = 2
                while output.exists():
                    output = output.with_name(f"{Path(filename).stem}_{number}.docx")
                    number += 1
                self.filename.setText(output.name)
            elif box.clickedButton() is replace:
                overwrite = True
            else:
                return
        inputs, source, settings = self.inputs(), self.info.path, self.settings()
        self.result_actions.hide()

        def work(cancel, progress):
            def report(value):
                self.detailed_progress.emit(value)
                progress(value.processed, value.total)

            return generate(inputs, source, output, settings, cancel, report, overwrite=overwrite)

        def done(result, error):
            if error:
                if not isinstance(error, Cancelled):
                    record_error("Word generation", error)
                self.status.setText(
                    "Cancelled. No output was saved."
                    if isinstance(error, Cancelled)
                    else str(error)
                )
                return
            self.output_path = result.path
            self.status.setText(
                f"Word document generated successfully!\nOriginal pages: "
                f"{result.original_pages} · PDF files: {result.pdf_files} · "
                f"New pages: {result.added_pages} · Final pages: {result.final_pages}\n"
                "Passed: page count, embedded image count/order/placement, "
                "header/footer and original content preservation, source hashes, "
                "saved document reopen."
            )
            self.result_actions.show()

        self.owner.run_job(work, "Generating Word document…", done)

    def report(self, value):
        remaining = (
            (value.total - value.processed) * value.elapsed / value.processed
            if value.processed
            else None
        )
        text = (
            f"{value.stage}\n{value.filename} · PDF page {value.page}/{value.file_pages}\n"
            f"Images processed / Word pages appended: {value.processed}/{value.total}\n"
            f"Elapsed: {value.elapsed:.0f}s"
            + (f" · Estimated remaining: {remaining:.0f}s" if remaining is not None else "")
        )
        self.status.setText(text)
        if self.owner.processing:
            self.owner.processing.label.setText(text)

    def open_output(self):
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path)))

    def open_folder(self):
        if self.output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path.parent)))

    def reset(self):
        self.clear()
        self.info = None
        self.word_info.setText("Select an existing Word document.")
        self.status.clear()
        self.result_actions.hide()
        self.refresh()
