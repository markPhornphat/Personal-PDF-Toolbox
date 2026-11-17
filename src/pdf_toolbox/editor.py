from dataclasses import dataclass, field, replace
from math import atan2, degrees
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QBuffer, QIODevice, QMarginsF, QPointF, QRectF, QSizeF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QImage,
    QKeySequence,
    QPageLayout,
    QPageSize,
    QPainter,
    QPainterPath,
    QPdfWriter,
    QPen,
    QShortcut,
    QTextDocument,
    QTextOption,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDoubleSpinBox,
    QFontComboBox,
    QFormLayout,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .pdf import safe_local
from .viewer import PageList, Thumbnails, Viewer, local_paths, page_item

SHAPES = (
    "Rectangle",
    "Rounded rectangle",
    "Ellipse",
    "Circle",
    "Line",
    "Arrow",
    "Freehand",
    "Highlight",
    "Filled rectangle",
)


def load_fonts(resources):
    return QFontDatabase.addApplicationFont(str(resources / "resources/fonts/NotoSansThai.ttf"))


@dataclass
class Object:
    kind: str
    x: float
    y: float
    width: float = 125
    height: float = 50
    angle: float = 0
    opacity: float = 1
    color: str = "#182738"
    fill: str = "#00000000"
    stroke: float = 2
    text: str = ""
    family: str = "Segoe UI"
    size: float = 16
    bold: bool = False
    italic: bool = False
    underline: bool = False
    align: str = "Left"
    aspect: bool = True
    image: QImage = field(default_factory=QImage)
    points: tuple[tuple[float, float], ...] = ()


def paint_object(painter, obj):
    box = QRectF(0, 0, obj.width, obj.height)
    painter.save()
    painter.setOpacity(obj.opacity)
    painter.setPen(QPen(QColor(obj.color), obj.stroke))
    painter.setBrush(QColor(obj.fill))
    if obj.kind == "Text":
        font = QFont(obj.family)
        font.setFamilies([obj.family, "Noto Sans Thai"])
        font.setPixelSize(round(obj.size))
        font.setBold(obj.bold)
        font.setItalic(obj.italic)
        font.setUnderline(obj.underline)
        document = QTextDocument()
        document.setDocumentMargin(0)
        document.setDefaultFont(font)
        document.setDefaultStyleSheet(f"body {{ color: {obj.color}; }}")
        alignments = {
            "Left": Qt.AlignmentFlag.AlignLeft,
            "Center": Qt.AlignmentFlag.AlignHCenter,
            "Right": Qt.AlignmentFlag.AlignRight,
        }
        option = QTextOption(alignments[obj.align])
        option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        document.setDefaultTextOption(option)
        document.setPlainText(obj.text)
        cursor = document.rootFrame().firstCursorPosition()
        cursor.select(cursor.SelectionType.Document)
        style = cursor.charFormat()
        style.setForeground(QColor(obj.color))
        cursor.mergeCharFormat(style)
        document.setTextWidth(obj.width)
        painter.setClipRect(box)
        document.drawContents(painter, box)
    elif obj.kind == "Image":
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering)
        painter.drawImage(box, obj.image)
    elif obj.kind in {"Ellipse", "Circle"}:
        painter.drawEllipse(box)
    elif obj.kind == "Rounded rectangle":
        painter.drawRoundedRect(box, 8, 8)
    elif obj.kind in {"Arrow", "Line"}:
        painter.drawLine(box.bottomLeft(), box.topRight())
        if obj.kind == "Arrow":
            tip = box.topRight()
            length = max(1, (box.width() ** 2 + box.height() ** 2) ** 0.5)
            direction = QPointF(-box.width() / length, box.height() / length)
            normal = QPointF(-direction.y(), direction.x())
            painter.drawLine(tip, tip + 13 * direction + 5 * normal)
            painter.drawLine(tip, tip + 13 * direction - 5 * normal)
    elif obj.kind == "Freehand" and obj.points:
        first, *rest = obj.points
        path = QPainterPath(QPointF(first[0] * obj.width, first[1] * obj.height))
        for x, y in rest:
            path.lineTo(x * obj.width, y * obj.height)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    else:
        painter.drawRect(box)
    painter.restore()


def make_overlay(objects, width, height):
    """Export the same shaped Qt text, paths and images used by the canvas."""
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    writer = QPdfWriter(buffer)
    writer.setResolution(720)
    size = QPageSize(
        QSizeF(width, height), QPageSize.Unit.Point, "Overlay", QPageSize.SizeMatchPolicy.ExactMatch
    )
    writer.setPageLayout(
        QPageLayout(
            size,
            QPageLayout.Orientation.Portrait,
            QMarginsF(),
            QPageLayout.Unit.Point,
        )
    )
    painter = QPainter(writer)
    painter.scale(10, 10)
    for obj in objects:
        painter.save()
        painter.translate(obj.x, obj.y)
        painter.rotate(obj.angle)
        paint_object(painter, obj)
        painter.restore()
    painter.end()
    return bytes(buffer.data())


class DrawingItem(QGraphicsItem):
    def __init__(self, obj):
        super().__init__()
        self.obj = obj
        self.resize_start = None
        self.rotate_start = None
        self.setPos(obj.x, obj.y)
        self.setRotation(obj.angle)
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        )

    def boundingRect(self):
        padding = max(6, self.obj.stroke)
        return QRectF(0, 0, self.obj.width, self.obj.height).adjusted(
            -padding, -22, padding, padding
        )

    def rotation_handle(self):
        return QPointF(self.obj.width / 2, -15)

    def paint(self, painter, option, widget=None):
        paint_object(painter, self.obj)
        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#177aef"), 1, Qt.PenStyle.DashLine))
            painter.drawRect(QRectF(0, 0, self.obj.width, self.obj.height))
            painter.fillRect(
                QRectF(self.obj.width - 5, self.obj.height - 5, 10, 10), QColor("#177aef")
            )
            handle = self.rotation_handle()
            painter.setBrush(QColor("#177aef"))
            painter.drawLine(QPointF(handle.x(), 0), handle)
            painter.drawEllipse(handle, 4, 4)

    def pointer_angle(self, scene_point):
        offset = scene_point - self.scenePos()
        return degrees(atan2(offset.y(), offset.x()))

    def mousePressEvent(self, event):
        point = event.pos()
        if self.isSelected() and (point - self.rotation_handle()).manhattanLength() <= 9:
            self.rotate_start = self.rotation() - self.pointer_angle(event.scenePos())
            event.accept()
            return
        if (
            self.isSelected()
            and abs(point.x() - self.obj.width) <= 7
            and abs(point.y() - self.obj.height) <= 7
        ):
            self.resize_start = self.obj
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.rotate_start is not None:
            self.setRotation(self.rotate_start + self.pointer_angle(event.scenePos()))
            return
        if self.resize_start is None:
            super().mouseMoveEvent(event)
            return
        self.prepareGeometryChange()
        width = max(5.0, event.pos().x())
        height = max(5.0, event.pos().y())
        if (self.obj.kind == "Image" and self.obj.aspect) or self.obj.kind == "Circle":
            height = width * self.resize_start.height / self.resize_start.width
        self.obj = replace(self.obj, width=width, height=height)
        self.update()

    def mouseReleaseEvent(self, event):
        if self.rotate_start is not None:
            self.rotate_start = None
            event.accept()
            return
        if self.resize_start is not None:
            self.resize_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def snapshot(self):
        return replace(self.obj, x=self.x(), y=self.y(), angle=self.rotation())


class Canvas(QGraphicsView):
    committed = Signal()
    inserted = Signal(object)
    edited = Signal()
    dropped = Signal(object, object)

    def __init__(self, scene):
        super().__init__(scene)
        self.tool = "Select"
        self.start = None
        self.points = []
        self.guide = None
        self.setAcceptDrops(True)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )

    def mousePressEvent(self, event):
        position = self.mapToScene(event.position().toPoint())
        if (
            self.tool != "Select"
            and self.dragMode() != self.DragMode.ScrollHandDrag
            and event.button() == Qt.MouseButton.LeftButton
            and self.sceneRect().contains(position)
        ):
            self.start = position
            self.points = [position]
            self.guide = self.scene().addRect(QRectF(position, position), QPen(QColor("#177aef")))
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.start is None:
            super().mouseMoveEvent(event)
            return
        point = self.mapToScene(event.position().toPoint())
        self.points.append(point)
        self.guide.setRect(QRectF(self.start, point).normalized())

    def mouseReleaseEvent(self, event):
        if self.start is None:
            super().mouseReleaseEvent(event)
            self.committed.emit()
            return
        end = self.mapToScene(event.position().toPoint())
        rect = QRectF(self.start, end).normalized()
        self.scene().removeItem(self.guide)
        self.guide = None
        self.start = None
        if self.tool == "Freehand":
            points = [*self.points, end]
            left, right = min(p.x() for p in points), max(p.x() for p in points)
            top, bottom = min(p.y() for p in points), max(p.y() for p in points)
            width, height = max(1, right - left), max(1, bottom - top)
            obj = Object(
                self.tool,
                left,
                top,
                width,
                height,
                points=tuple(((p.x() - left) / width, (p.y() - top) / height) for p in points),
            )
        else:
            width = rect.width() if rect.width() > 3 else 125
            height = rect.height() if rect.height() > 3 else 50
            if self.tool == "Circle":
                height = width
            obj = Object(self.tool, rect.x(), rect.y(), width, height)
        if self.tool == "Highlight":
            obj = replace(obj, fill="#ffff39", color="#ffff39", opacity=0.32)
        elif self.tool == "Filled rectangle":
            obj = replace(obj, fill="#78aee9")
        self.inserted.emit(obj)

    def mouseDoubleClickEvent(self, event):
        super().mouseDoubleClickEvent(event)
        self.edited.emit()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.dropped.emit(event.mimeData(), self.mapToScene(event.position().toPoint()))
        event.acceptProposedAction()

    def keyPressEvent(self, event):
        movement = {
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_Down: (0, 1),
        }.get(event.key())
        if movement and self.scene().selectedItems():
            for item in self.scene().selectedItems():
                item.moveBy(*movement)
            self.committed.emit()
        else:
            super().keyPressEvent(event)


class Editor(QWidget):
    changed = Signal()
    alert = Signal(str)
    open_requested = Signal(list)

    def __init__(self, jobs, thumbnails):
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.canvas = Canvas(self.scene)
        self.viewer = Viewer(jobs, self.scene, self.canvas)
        self.pages = PageList(reorder=False)
        self.pages.setMaximumWidth(185)
        self.thumbnails = Thumbnails(self.pages, thumbnails)
        self.objects: dict[int, list[Object]] = {}
        self.sizes = {}
        self.history: list[dict[int, list[Object]]] = [{}]
        self.cursor = 0
        self.saved = {}
        self.references = []
        self.index = -1
        self.pending_images = []
        self.copied_objects: list[Object] = []
        self.clipboard_token = b""
        self.loading = False
        self.refreshing = False
        self.properties = self.build_inspector()

        panel = QHBoxLayout(self)
        splitter = QSplitter()
        panel.addWidget(splitter)
        splitter.addWidget(self.pages)
        central = QWidget()
        controls = QVBoxLayout(central)
        toolbar = QHBoxLayout()
        self.tool = QComboBox()
        self.tool.addItems(["Select", "Text", *SHAPES])
        self.tool.currentTextChanged.connect(self.choose_tool)
        toolbar.addWidget(self.tool)
        for label, callback in [
            ("Insert image", self.browse_image),
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Delete", self.delete),
        ]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
        toolbar.addStretch()
        controls.addLayout(toolbar)
        controls.addWidget(self.viewer)
        splitter.addWidget(central)
        splitter.addWidget(self.properties)
        splitter.setSizes([160, 720, 220])
        self.pages.currentRowChanged.connect(self.show_page)
        self.pages.files_dropped.connect(self.open_requested)
        self.viewer.on_previous = lambda: self.navigate(-1)
        self.viewer.on_next = lambda: self.navigate(1)
        self.viewer.shown.connect(self.page_ready)
        self.canvas.inserted.connect(self.add)
        self.canvas.dropped.connect(self.paste)
        self.canvas.committed.connect(self.commit)
        self.canvas.edited.connect(lambda: self.text.setFocus() if self.text.isEnabled() else None)
        self.scene.selectionChanged.connect(self.inspect)
        self.canvas.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.canvas.customContextMenuRequested.connect(self.context_menu)
        for sequence, callback in [
            ("Delete", self.delete),
            ("Ctrl+D", self.duplicate),
            ("Ctrl+C", self.copy_objects),
            ("Ctrl+X", self.cut),
            ("Ctrl+Z", self.undo),
            ("Ctrl+Y", self.redo),
        ]:
            shortcut = QShortcut(QKeySequence(sequence), self.canvas)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(callback)
        self.inspect()

    def build_inspector(self):
        widget = QWidget()
        form = QFormLayout(widget)
        form.addRow(QLabel("Object properties"))
        self.text = QTextEdit()
        self.text.setAcceptRichText(False)
        self.text.setMaximumHeight(102)
        form.addRow("Text", self.text)
        self.font = QFontComboBox()
        form.addRow("Font", self.font)
        self.align = QComboBox()
        self.align.addItems(["Left", "Center", "Right"])
        form.addRow("Align", self.align)
        self.options = {}
        for key, title, low, high in [
            ("size", "Font size", 5, 240),
            ("width", "Width", 1, 5000),
            ("height", "Height", 1, 5000),
            ("angle", "Rotation", -360, 360),
            ("opacity", "Opacity %", 1, 100),
            ("stroke", "Border width", 0, 30),
        ]:
            box = QDoubleSpinBox()
            box.setRange(low, high)
            box.setDecimals(1)
            box.setKeyboardTracking(False)
            box.valueChanged.connect(
                lambda value, name=key: self.modify(
                    name, value / 100 if name == "opacity" else value
                )
            )
            self.options[key] = box
            form.addRow(title, box)
        self.flags = {}
        for key, title in [
            ("bold", "Bold"),
            ("italic", "Italic"),
            ("underline", "Underline"),
            ("aspect", "Lock aspect ratio"),
        ]:
            button = QCheckBox(title)
            button.toggled.connect(lambda value, name=key: self.modify(name, value))
            self.flags[key] = button
            form.addRow(button)
        for key, title in [("color", "Text / border color"), ("fill", "Fill color")]:
            button = QPushButton(title)
            button.clicked.connect(lambda _, name=key: self.choose_color(name))
            form.addRow(button)
        self.text.textChanged.connect(lambda: self.modify("text", self.text.toPlainText()))
        self.font.currentFontChanged.connect(lambda font: self.modify("family", font.family()))
        self.align.currentTextChanged.connect(lambda value: self.modify("align", value))
        return widget

    def inspect(self):
        selected = self.selected()
        self.properties.setEnabled(len(selected) == 1)
        if len(selected) != 1:
            return
        self.refreshing = True
        obj = selected[0].snapshot()
        if self.text.toPlainText() != obj.text:
            self.text.setPlainText(obj.text)
        self.text.setEnabled(obj.kind == "Text")
        self.font.setEnabled(obj.kind == "Text")
        self.align.setEnabled(obj.kind == "Text")
        self.font.setCurrentFont(QFont(obj.family))
        self.align.setCurrentText(obj.align)
        for key, box in self.options.items():
            box.setValue(getattr(obj, key) * (100 if key == "opacity" else 1))
        for key, button in self.flags.items():
            button.setChecked(getattr(obj, key))
        self.refreshing = False

    def modify(self, name, value):
        selected = self.selected()
        if self.refreshing or len(selected) != 1:
            return
        item = selected[0]
        obj = item.snapshot()
        changes = {name: value}
        if (obj.kind == "Image" and obj.aspect) or obj.kind == "Circle":
            if name == "width":
                changes["height"] = value * obj.height / obj.width
            elif name == "height":
                changes["width"] = value * obj.width / obj.height
        item.prepareGeometryChange()
        item.obj = replace(obj, **changes)
        item.setRotation(item.obj.angle)
        item.update()
        self.commit()

    def choose_color(self, name):
        selected = self.selected()
        if len(selected) == 1:
            color = QColorDialog.getColor(
                QColor(getattr(selected[0].obj, name)),
                self,
                "Choose color",
                QColorDialog.ColorDialogOption.ShowAlphaChannel,
            )
            if color.isValid():
                self.modify(name, color.name(QColor.NameFormat.HexArgb))

    def choose_tool(self, title):
        self.canvas.tool = title
        self.canvas.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

    def set_document(self, references):
        self.pages.blockSignals(True)
        self.pages.clear()
        self.pages.blockSignals(False)
        self.references = references
        self.index = -1
        self.objects = {}
        self.saved = {}
        self.history = [{}]
        self.cursor = 0
        self.sizes.clear()
        self.thumbnails.clear()
        for page in references:
            self.pages.addItem(page_item(page))
        self.pages.setCurrentRow(0)

    def navigate(self, delta):
        row = self.pages.currentRow() + delta
        if 0 <= row < self.pages.count():
            self.pages.setCurrentRow(row)

    def show_page(self, index):
        self.index = index
        self.clear_items()
        if not 0 <= index < len(self.references):
            self.viewer.load(None, 0, 0)
            return
        self.loading = True
        self.viewer.load(self.references[index], index, len(self.references))

    def page_ready(self, page, size):
        self.sizes[self.index] = size
        self.loading = False
        self.restore_items()
        for image in self.pending_images:
            self.add_image(image, QPointF(24, 24))
        self.pending_images.clear()

    def items(self):
        return [
            item
            for item in self.scene.items(Qt.SortOrder.AscendingOrder)
            if isinstance(item, DrawingItem)
        ]

    def selected(self):
        return [item for item in self.items() if item.isSelected()]

    def clear_items(self):
        for item in self.items():
            self.scene.removeItem(item)

    def restore_items(self):
        self.clear_items()
        for index, obj in enumerate(self.objects.get(self.index, [])):
            item = DrawingItem(obj)
            item.setZValue(index)
            self.scene.addItem(item)

    def add(self, obj):
        if self.loading or self.index < 0:
            return
        self.scene.clearSelection()
        item = DrawingItem(obj)
        item.setZValue(len(self.items()))
        self.scene.addItem(item)
        item.setSelected(True)
        self.commit()
        if obj.kind == "Text" and not obj.text:
            self.text.setFocus()
        self.tool.setCurrentText("Select")

    def commit(self):
        if self.loading or self.index < 0:
            return
        state = dict(self.objects)
        items = [item.snapshot() for item in self.items()]
        if items:
            state[self.index] = items
        else:
            state.pop(self.index, None)
        if state != self.objects:
            self.objects = state
            self.history = [*self.history[: self.cursor + 1], state][-100:]
            self.cursor = len(self.history) - 1
            self.inspect()
            self.changed.emit()

    def undo(self):
        if self.cursor > 0:
            self.cursor -= 1
            self.restore()

    def redo(self):
        if self.cursor < len(self.history) - 1:
            self.cursor += 1
            self.restore()

    def restore(self):
        self.objects = self.history[self.cursor]
        if not self.loading:
            self.restore_items()
        self.changed.emit()

    def delete(self):
        for item in self.selected():
            self.scene.removeItem(item)
        self.commit()

    def duplicate(self):
        for item in self.selected():
            obj = item.snapshot()
            self.add(replace(obj, x=obj.x + 12, y=obj.y + 12))

    def copy_objects(self):
        from PySide6.QtCore import QMimeData

        items = [item.snapshot() for item in self.selected()]
        if not items:
            return
        data = QMimeData()
        self.clipboard_token = uuid4().bytes
        self.copied_objects = items
        data.setData("application/x-pdf-toolbox-objects", self.clipboard_token)
        if len(items) == 1 and items[0].kind == "Text":
            data.setText(items[0].text)
        QApplication.clipboard().setMimeData(data)

    def cut(self):
        self.copy_objects()
        self.delete()

    def browse_image(self):
        from PySide6.QtWidgets import QFileDialog

        name, _ = QFileDialog.getOpenFileName(
            self, "Insert image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if name and safe_local(Path(name)):
            self.add_image(QImage(name), QPointF(24, 24))

    def paste(self, mime, position=None):
        paths = [path for path in local_paths(mime) if safe_local(path)]
        pdfs = [path for path in paths if path.suffix.lower() == ".pdf"]
        if pdfs:
            self.open_requested.emit(pdfs)
            return
        point = (
            position
            if position is not None
            else self.canvas.mapToScene(self.canvas.viewport().rect().center())
        )
        token = bytes(mime.data("application/x-pdf-toolbox-objects"))
        if token and token == self.clipboard_token:
            for obj in self.copied_objects:
                self.add(replace(obj, x=obj.x + 12, y=obj.y + 12))
        elif mime.hasImage():
            self.add_image(QImage(mime.imageData()), point)
        elif paths:
            for path in paths:
                if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg"}:
                    self.add_image(QImage(str(path)), point)
                else:
                    self.alert.emit("Choose a PDF, JPG or PNG file.")
        elif mime.hasText():
            self.add(Object("Text", point.x(), point.y(), 220, 100, text=mime.text()))

    def add_image(self, image, point):
        if image.isNull():
            self.alert.emit("This image could not be opened.")
            return
        if self.index < 0:
            self.alert.emit("Open a PDF before inserting an image.")
            return
        if image.width() * image.height() > 32_000_000:
            self.alert.emit("This image is too large. Resize it before inserting.")
            return
        if self.loading:
            self.pending_images.append(image)
            return
        width = min(self.scene.sceneRect().width() * 0.65, image.width())
        self.add(
            Object(
                "Image",
                point.x(),
                point.y(),
                width,
                width * image.height() / image.width(),
                image=image,
            )
        )

    def context_menu(self, point):
        menu = QMenu(self)
        for label, callback in [
            ("Copy", self.copy_objects),
            ("Cut", self.cut),
            ("Duplicate", self.duplicate),
            ("Delete", self.delete),
            ("Bring forward", lambda: self.stack("forward")),
            ("Send backward", lambda: self.stack("backward")),
            ("Bring to front", lambda: self.stack("front")),
            ("Send to back", lambda: self.stack("back")),
        ]:
            menu.addAction(label, callback)
        menu.exec(self.canvas.viewport().mapToGlobal(point))

    def stack(self, direction):
        items = self.items()
        chosen = self.selected()
        if direction == "front":
            items = [item for item in items if item not in chosen] + chosen
        elif direction == "back":
            items = chosen + [item for item in items if item not in chosen]
        elif direction == "forward":
            for index in range(len(items) - 2, -1, -1):
                if items[index] in chosen and items[index + 1] not in chosen:
                    items[index], items[index + 1] = items[index + 1], items[index]
        else:
            for index in range(1, len(items)):
                if items[index] in chosen and items[index - 1] not in chosen:
                    items[index], items[index - 1] = items[index - 1], items[index]
        for index, item in enumerate(items):
            item.setZValue(index)
        self.commit()

    def overlays(self):
        return {
            index: make_overlay(items, *self.sizes[index]) for index, items in self.objects.items()
        }

    @property
    def dirty(self):
        return self.objects != self.saved
