from collections import OrderedDict

from PySide6.QtCore import QItemSelectionModel, QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .pdf import check_cancelled, page_size, render


def preview(page, pixels):
    image = render(page, pixels=pixels).convert("RGB")
    return QImage(
        image.tobytes(), image.width, image.height, image.width * 3, QImage.Format.Format_RGB888
    ).copy(), page_size(page)


class PageList(QListWidget):
    files_dropped = Signal(list)
    reordered = Signal()

    def __init__(self, reorder=True):
        super().__init__()
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIconSize(QSize(84, 110))
        self.setGridSize(QSize(136, 160))
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setUniformItemSizes(True)
        self.setSpacing(6)
        self.drop_mark = None
        if reorder:
            self.setMovement(QListWidget.Movement.Snap)
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            self.setDropIndicatorShown(True)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        elif event.source() is self:
            point = event.position().toPoint()
            item = self.itemAt(point)
            if item is None and self.count():
                item = self.item(self.count() - 1)
            if item is not None:
                rect = self.visualItemRect(item)
                x = rect.right() if point.x() >= rect.center().x() else rect.left()
                self.drop_mark = QPoint(x, rect.center().y())
                self.viewport().update()
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def startDrag(self, supported_actions):
        items = self.selectedItems()
        if items:
            drag = QDrag(self)
            drag.setMimeData(self.mimeData(items))
            drag.exec(Qt.DropAction.MoveAction)

    def dragLeaveEvent(self, event):
        self.drop_mark = None
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.drop_mark is not None:
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor("#177aef"), 3))
            painter.drawLine(self.drop_mark - QPoint(0, 25), self.drop_mark + QPoint(0, 25))
            painter.end()

    def dropEvent(self, event):
        self.drop_mark = None
        self.viewport().update()
        if event.mimeData().hasUrls():
            self.files_dropped.emit(local_paths(event.mimeData()))
            event.acceptProposedAction()
            return
        if event.source() is not self or self.dragDropMode() != self.DragDropMode.InternalMove:
            event.ignore()
            return
        point = event.position().toPoint()
        item = self.itemAt(point)
        target = self.row(item) if item else self.count()
        if item and point.x() > self.visualItemRect(item).center().x():
            target += 1
        rows = sorted(self.row(item) for item in self.selectedItems())
        target -= sum(row < target for row in rows)
        self.blockSignals(True)
        moving = [self.takeItem(row) for row in reversed(rows)]
        self.clearSelection()
        for index, moved in enumerate(reversed(moving), target):
            self.insertItem(index, moved)
            moved.setSelected(True)
        self.blockSignals(False)
        if moving:
            self.setCurrentItem(moving[-1], QItemSelectionModel.SelectionFlag.NoUpdate)
            self.reordered.emit()
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()


def local_paths(mime):
    from pathlib import Path

    return [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]


class Viewer(QWidget):
    shown = Signal(object, object)

    def __init__(self, jobs, scene=None, view=None):
        super().__init__()
        self.jobs = jobs
        self.scene = scene if scene is not None else QGraphicsScene(self)
        self.view = view if view is not None else QGraphicsView(self.scene)
        self.image = QGraphicsPixmapItem()
        self.image.setZValue(-1000)
        self.scene.addItem(self.image)
        self.counter = QLabel("No page selected")
        self.status = QLabel()
        self.page = None
        self.generation = 0
        self.rendering = None
        self.fit_mode = "page"
        self.on_previous = lambda: None
        self.on_next = lambda: None

        layout = QVBoxLayout(self)
        tools = QHBoxLayout()
        for title, slot in [
            ("Previous", lambda: self.on_previous()),
            ("Next", lambda: self.on_next()),
            ("−", lambda: self.zoom(0.8)),
            ("+", lambda: self.zoom(1.25)),
            ("Fit page", lambda: self.fit("page")),
            ("Fit width", lambda: self.fit("width")),
            ("Pan", self.pan),
        ]:
            button = QPushButton(title)
            button.clicked.connect(slot)
            tools.addWidget(button)
        tools.addWidget(self.counter)
        tools.addStretch()
        layout.addLayout(tools)
        layout.addWidget(self.view)
        layout.addWidget(self.status)

    def load(self, page, index, count):
        if self.rendering:
            self.rendering.set()
        self.generation += 1
        generation = self.generation
        self.page = page
        self.image.setPixmap(QPixmap())
        self.counter.setText(f"Page {index + 1} of {count}" if page else "No page selected")
        self.status.setText("Rendering page…" if page else "")
        if not page:
            return

        def done(value, error):
            if generation != self.generation:
                return
            if error:
                self.status.setText("This page could not be rendered.")
                return
            picture, (width, height) = value
            self.image.setPixmap(QPixmap.fromImage(picture))
            self.image.setScale(width / picture.width())
            self.scene.setSceneRect(0, 0, width, height)
            self.status.clear()
            self.fit(self.fit_mode)
            self.shown.emit(page, (width, height))

        def work(cancelled, _):
            check_cancelled(cancelled)
            return preview(page, 1500)

        self.rendering = self.jobs.submit(work, done)

    def fit(self, mode):
        self.fit_mode = mode
        rect = self.scene.sceneRect()
        if rect.isEmpty() or mode == "manual":
            return
        if mode == "width":
            self.view.resetTransform()
            ratio = max(1, self.view.viewport().width() - 24) / rect.width()
            self.view.scale(ratio, ratio)
        else:
            self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self, lambda: self.fit(self.fit_mode))

    def zoom(self, factor):
        target = self.view.transform().m11() * factor
        if 0.03 <= target <= 16:
            self.fit_mode = "manual"
            self.view.scale(factor, factor)

    def pan(self):
        mode = self.view.dragMode()
        self.view.setDragMode(
            QGraphicsView.DragMode.RubberBandDrag
            if mode == QGraphicsView.DragMode.ScrollHandDrag
            else QGraphicsView.DragMode.ScrollHandDrag
        )


class Thumbnails:
    def __init__(self, listing, jobs):
        self.listing = listing
        self.jobs = jobs
        self.cache = OrderedDict()
        self.pending = set()
        self.timer = QTimer(listing)
        self.timer.setInterval(160)
        self.timer.timeout.connect(self.fill)
        self.timer.start()

    def fill(self):
        if not self.listing.isVisible():
            return
        viewport = self.listing.viewport()
        rect = viewport.rect()
        sample = self.listing.indexAt(QPoint(rect.left() + 20, 15))
        if not sample.isValid():
            sample = self.listing.indexAt(QPoint(rect.left() + 60, 65))
        start = max(0, sample.row() - 12) if sample.isValid() else 0
        if not sample.isValid() and self.listing.verticalScrollBar().maximum():
            scroll = self.listing.verticalScrollBar()
            start = max(0, int(self.listing.count() * scroll.value() / scroll.maximum()) - 45)
        visible = []
        for index in range(start, min(start + 150, self.listing.count())):
            item = self.listing.item(index)
            if self.listing.visualItemRect(item).intersects(rect):
                visible.append(item)
        for index in range(self.listing.count()):
            item = self.listing.item(index)
            if not item.icon().isNull() and item not in visible:
                item.setIcon(QIcon())
        for item in visible:
            page = item.data(Qt.ItemDataRole.UserRole)
            if page in self.cache:
                item.setIcon(self.cache[page])
                self.cache.move_to_end(page)
            elif page not in self.pending and len(self.pending) < 4:
                self.pending.add(page)
                self.jobs.submit(
                    lambda *_, p=page: preview(p, 104),
                    lambda value, error, p=page: self.done(p, value, error),
                )

    def done(self, page, value, error):
        self.pending.discard(page)
        if not error:
            self.cache[page] = QIcon(QPixmap.fromImage(value[0]))
        else:
            self.cache[page] = QIcon()
        if len(self.cache) > 128:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


def page_item(page):
    item = QListWidgetItem(f"{page.path.stem}\nPage {page.index + 1}")
    item.setToolTip(f"{page.path.name} · Page {page.index + 1}")
    item.setData(Qt.ItemDataRole.UserRole, page)
    return item
