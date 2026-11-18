from datetime import datetime
import ctypes
import os

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from .appearance import tool_icon
from .localization import describe_button, tr


def startup_check_key():
    boot = "unknown"
    if os.name == "nt":
        data = ctypes.create_string_buffer(48)
        if ctypes.windll.ntdll.NtQuerySystemInformation(3, data, len(data), None) == 0:
            boot = str(ctypes.c_longlong.from_buffer(data).value)
    return f"{datetime.now().date().isoformat()}/{boot}"


class UpdateNotice(QDialog):
    def __init__(self, window, release):
        super().__init__(window)
        self.setObjectName("UpdateNotice")
        self.setWindowTitle(tr(window, "Update available"))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setModal(False)
        self.setFixedWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        title = QLabel(tr(window, "A new version is ready"))
        title.setObjectName("Section")
        title.setWordWrap(True)
        layout.addWidget(title)
        version = QLabel(tr(window, "Version {version}", version=release.manifest.version))
        version.setObjectName("AboutVersion")
        layout.addWidget(version, alignment=Qt.AlignmentFlag.AlignLeft)
        body = QLabel(tr(window, "Update now to install and reopen PDF Toolbox automatically."))
        body.setWordWrap(True)
        layout.addWidget(body)
        actions = QHBoxLayout()
        self.later = QPushButton(tr(window, "Remind me later"))
        self.update = QPushButton(
            tool_icon("export", window.theme_palette["on_primary"]), tr(window, "Update now")
        )
        self.update.setProperty("primary", True)
        for button, label in ((self.later, "Remind me later"), (self.update, "Update now")):
            describe_button(button, window, label)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.later.clicked.connect(self.reject)
        self.update.clicked.connect(lambda: window.start_update())

    def position_at_corner(self):
        self.adjustSize()
        window = self.parentWidget()
        screen = window.screen().availableGeometry()
        corner = window.mapToGlobal(window.rect().bottomRight()) - QPoint(18, 43)
        right = min(corner.x(), screen.right() - 14)
        bottom = min(corner.y(), screen.bottom() - 14)
        self.move(
            max(screen.left(), right - self.width()), max(screen.top(), bottom - self.height())
        )
