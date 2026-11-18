from math import cos, pi, sin

from PySide6.QtCore import QEasingCurve, QElapsedTimer, QRectF, Qt, QTimer, QVariantAnimation
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from .appearance import action_button, motion_enabled, tool_icon
from .localization import describe_button, tr


class DogWalk(QWidget):
    def __init__(self, picture, animate):
        super().__init__()
        self.picture = picture
        self.animate = animate
        self.fraction = None
        self.setFixedHeight(69)
        self.elapsed = QElapsedTimer()
        self.animation = QTimer(self, interval=16)
        self.animation.timeout.connect(self.update)

    def showEvent(self, event):
        super().showEvent(event)
        self.elapsed.start()
        if self.animate:
            self.animation.start()

    def hideEvent(self, event):
        self.animation.stop()
        super().hideEvent(event)

    def paintEvent(self, _event):
        seconds = self.elapsed.elapsed() / 1000 if self.animate and self.elapsed.isValid() else 0
        lap = seconds / 4.2 % 2
        fraction = self.fraction if self.fraction is not None else min(lap, 2 - lap)
        stride = seconds * 2.2 * pi
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        painter.translate(2 + (self.width() - 66) * fraction, 0)
        if self.fraction is None and lap > 1:
            painter.translate(62, 0)
            painter.scale(-1, 1)
        painter.setPen(Qt.PenStyle.NoPen)
        for x, phase in ((24, stride + pi), (45, stride)):
            painter.setBrush(QColor("#b5794f"))
            painter.drawEllipse(QRectF(x + 5 * sin(phase), 52 - 4 * max(0, cos(phase)), 13, 16))
            painter.setBrush(QColor("#f0c58e"))
            painter.drawEllipse(QRectF(x - 5 * sin(phase), 55 - 4 * max(0, -cos(phase)), 13, 13))
        painter.drawPixmap(
            QRectF(0, abs(sin(stride)) * 3, 62, 62), self.picture, QRectF(self.picture.rect())
        )


class ProcessingDialog(QDialog):
    cancel_requested = Signal()

    def __init__(self, parent, label, picture, palette, *, show_details=False):
        super().__init__(parent)
        self.setWindowTitle("PDF Toolbox")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 19, 24, 20)
        layout.setSpacing(8)
        self.label = QLabel(tr(parent, label))
        self.label.setObjectName("Section")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.dog = DogWalk(picture, motion_enabled(self))
        layout.addWidget(self.dog)
        self.target = None
        self.transition = QVariantAnimation(self, duration=280)
        self.transition.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.transition.valueChanged.connect(self.display_progress)
        self.bar = QProgressBar()
        self.bar.setAccessibleName(self.label.text())
        self.bar.setRange(0, 0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(12)
        self.bar.setStyleSheet(f"QProgressBar::chunk {{ background: {palette['primary']}; }}")
        layout.addWidget(self.bar)
        self.percent = QLabel()
        layout.addWidget(self.percent, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.hide()
        if show_details:
            self.toggle_details = action_button("down", "Show details")
            self.toggle_details.setCheckable(True)
            self.toggle_details.toggled.connect(self.expand_details)
            layout.addWidget(self.toggle_details, alignment=Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(self.details)
        self.cancel = QPushButton(tool_icon("close", palette["primary"]), tr(parent, "Cancel"))
        describe_button(self.cancel, parent, "Cancel")
        self.cancel.clicked.connect(self.reject)
        layout.addWidget(self.cancel, alignment=Qt.AlignmentFlag.AlignRight)

    @Slot(int, int)
    def report(self, current, total):
        if total > 0:
            target = min(max(current, 0), total) / total
            if self.target is not None and target <= self.target:
                return
            self.target = target
            self.transition.stop()
            self.bar.setRange(0, 1000)
            start = self.dog.fraction or 0.0
            self.display_progress(start)
            if not self.dog.animate or start == target:
                self.display_progress(target)
                return
            self.transition.setStartValue(start)
            self.transition.setEndValue(target)
            self.transition.start()

    def display_progress(self, fraction):
        self.bar.setValue(round(fraction * 1000))
        self.dog.fraction = fraction
        self.dog.update()
        percentage = 100 if fraction >= 1 else min(99, round(fraction * 100))
        if self.percent.text() != f"{percentage}%":
            self.percent.setText(f"{percentage}%")

    def expand_details(self, expanded):
        kind = "up" if expanded else "down"
        self.toggle_details.setProperty("iconKind", kind)
        self.toggle_details.setIcon(tool_icon(kind, self.parent().theme_palette["primary"]))
        self.toggle_details.setText("Hide details" if expanded else "Show details")
        self.details.setVisible(expanded)
        self.adjustSize()

    def reject(self):
        if self.cancel.isEnabled():
            self.cancel.setEnabled(False)
            self.cancel.setText(tr(self.parent(), "Cancelling…"))
            self.cancel_requested.emit()
