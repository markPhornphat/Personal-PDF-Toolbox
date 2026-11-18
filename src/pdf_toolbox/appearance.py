"""Desktop palette, line icons, and dashboard artwork."""

import ctypes
import os
from functools import lru_cache

from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QStyle, QVBoxLayout
from PySide6.QtWidgets import QWidget

LIGHT = {
    "background": "#fff8fa",
    "surface": "#ffffff",
    "field": "#fffbfd",
    "ink": "#382537",
    "muted": "#685166",
    "file_metadata": "#625b62",
    "border": "#e8d7e1",
    "primary": "#733d74",
    "pressed": "#5d2c60",
    "on_primary": "#ffffff",
    "hover": "#fbecf3",
    "selected": "#f3dced",
    "canvas": "#f1edf1",
    "rose": "#F5C6CE",
    "lilac": "#f1e5fa",
    "pistachio": "#e6f0d9",
    "butter": "#fff0ce",
    "focus": "#965388",
    "art": "#efd8f5",
    "organize": "#F5C6CE",
    "organize_ink": "#54283B",
    "organize_card": "#fbe5ea",
    "disabled": "#8d7586",
}
DARK = {
    "background": "#211925",
    "surface": "#2c2231",
    "field": "#302536",
    "ink": "#fff2fa",
    "muted": "#d3bbcd",
    "file_metadata": "#c6bdc8",
    "border": "#56405a",
    "primary": "#e1afe1",
    "pressed": "#f0c6ed",
    "on_primary": "#341d36",
    "hover": "#3b2b42",
    "selected": "#503650",
    "canvas": "#242028",
    "rose": "#492d43",
    "lilac": "#44334f",
    "pistachio": "#364533",
    "butter": "#4a3b31",
    "focus": "#e6afe3",
    "art": "#634365",
    "organize": "#F5C6CE",
    "organize_ink": "#54283B",
    "organize_card": "#492d43",
    "disabled": "#a48ba4",
}


def motion_enabled(widget):
    if not widget.style().styleHint(QStyle.StyleHint.SH_Widget_Animation_Duration):
        return False
    if os.name == "nt":
        spi_get_client_area_animation = 0x1042
        enabled = ctypes.c_int()
        read = ctypes.windll.user32.SystemParametersInfoW(
            spi_get_client_area_animation, 0, ctypes.byref(enabled), 0
        )
        if read:
            return bool(enabled.value)
    return True


def stylesheet(palette):
    style = """
    QWidget { color: $ink; font-family: "Nunito"; font-size: 14px; }
    QMainWindow, QDialog, QMessageBox, QMenu { background: $background; }
    QDialog#UpdateNotice { background: $surface; border: 2px solid $border; border-radius: 18px; }
    QLabel { background: transparent; }
    QLabel#Brand { font-size: 21px; font-weight: 850; }
    QLabel#BrandMark { background: $primary; border-radius: 12px; }
    QLabel#Heading { font-size: 30px; font-weight: 850; }
    QLabel#Section { font-size: 22px; font-weight: 850; }
    QLabel#DetailHeading, QPushButton#NavButton { font-size: 14px; font-weight: 750; }
    QLabel#HeroTitle { font-size: 41px; font-weight: 900; }
    QLabel#EmptyToolTitle { font-size: 36px; font-weight: 900; }
    QLabel#EmptyToolIcon { border-radius: 24px; }
    QLabel#EmptyToolIcon[tone="rose"] { background: $rose; }
    QLabel#EmptyToolIcon[tone="lilac"] { background: $lilac; }
    QLabel#EmptyToolIcon[tone="pistachio"] { background: $pistachio; }
    QLabel#EmptyToolIcon[tone="butter"] { background: $butter; }
    QLabel#EmptyToolIcon[tone="organize"] { background: $organize; }
    QFrame#ToolDropArea { background: $surface; border: 2px dashed $border; border-radius: 20px; }
    QFrame#ToolDropArea[dragging="true"] { background: $lilac; border-color: $focus; }
    QLabel#HeroHint, QLabel#ToolDescription, QLabel#Muted { color: $muted; }
    QLabel#HeroHint { font-size: 15px; font-weight: 600; }
    QLabel#ToolTitle { font-size: 17px; font-weight: 850; }
    QLabel#ToolDescription { font-size: 13px; font-weight: 600; }
    QFrame#Sidebar, QFrame[panel="true"] {
        background: $surface; border: 1px solid $border; border-radius: 22px;
    }
    QFrame#DropArea { background: $rose; border: 2px solid $rose; border-radius: 27px; }
    QFrame#DropArea[dragging="true"] { border: 2px dashed $focus; background: $lilac; }
    QFrame#Divider { background: $border; border: none; }
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
        background: $field; border: 1px solid $border; border-radius: 9px;
    }
    QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { padding: 6px 8px; }
    QLineEdit#ToolSearch { background: $surface; border-radius: 13px; padding: 8px 13px; }
    QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus,
    QTextEdit:focus, QListWidget:focus { border-color: $focus; }
    QComboBox QAbstractItemView {
        background: $surface; color: $ink; border: 1px solid $border;
        selection-background-color: $selected; selection-color: $ink;
    }
    QPushButton {
        background: transparent; border-radius: 9px; min-height: 25px;
        padding: 4px 11px; font-weight: 750;
    }
    QPushButton:hover { background: $hover; border-color: $focus; }
    QPushButton:focus { border-color: $focus; }
    QPushButton:pressed { background: $selected; }
    QPushButton:disabled { color: $disabled; border-color: $border; }
    QPushButton[primary="true"] {
        background: $primary; color: $on_primary; border-color: $primary;
    }
    QPushButton[primary="true"]:hover { background: $pressed; }
    QPushButton[primary="true"]:focus { border-color: $ink; }
    QPushButton[primary="true"]:disabled {
        background: $selected; color: $disabled; border-color: $border;
    }
    QPushButton#BrowsePrimary { border-radius: 12px; padding: 8px 19px; font-size: 15px; }
    QPushButton[iconOnly="true"] { padding: 3px 4px; }
    QPushButton#NavButton {
        text-align: left; background: transparent; border-color: transparent;
        min-height: 29px; padding: 5px 8px; border-radius: 11px;
    }
    QPushButton#NavButton:hover { background: $hover; }
    QPushButton#NavButton[active="true"] { background: $selected; }
    QPushButton#NavButton:focus { border-color: $focus; }
    QPushButton#ThemeButton { background: $field; padding: 4px; }
    QPushButton#ThemeButton:hover { background: $hover; }
    QFrame#AboutHero { background: $organize_card; border-radius: 17px; }
    QLabel#AboutVersion {
        background: $organize; color: $organize_ink; border-radius: 10px;
        font-size: 12px; font-weight: 850; padding: 3px 11px;
    }
    QPushButton#ToolCard { background: $surface; padding: 0; border-radius: 17px; }
    QPushButton#ToolCard[featured="true"] { background: $organize_card; }
    QPushButton#ToolCard:hover, QPushButton#ToolCard:focus { border: 2px solid $focus; }
    QPushButton#ToolCard:pressed { background: $selected; }
    QLabel#ToolIcon { border-radius: 12px; }
    QLabel#ToolIcon[tone="rose"] { background: $rose; }
    QLabel#ToolIcon[tone="lilac"] { background: $lilac; }
    QLabel#ToolIcon[tone="pistachio"] { background: $pistachio; }
    QLabel#ToolIcon[tone="butter"] { background: $butter; }
    QLabel#ToolIcon[tone="organize"] { background: $organize; }
    QListWidget {
        background: $surface; border: 1px solid $border; border-radius: 13px;
        selection-background-color: $selected; selection-color: $ink;
    }
    QListWidget::item:selected { background: $selected; color: $ink; }
    QScrollArea#WordPanel, QWidget#WordPanelBody { background: $background; }
    QListWidget#WordFiles { background: $canvas; padding: 4px; }
    QListWidget#WordFiles::item {
        background: $surface; border: 1px solid $border; border-radius: 9px;
        margin: 3px; padding: 4px 9px 4px 30px;
    }
    QListWidget#WordFiles::item:selected { background: $selected; border-color: $focus; }
    QListWidget#WordFiles::item:hover { border-color: $focus; }
    QGraphicsView { background: $canvas; border: 1px solid $border; border-radius: 14px; }
    QScrollArea#Inspector { background: $surface; border: 1px solid $border; border-radius: 14px; }
    QFrame#InspectorBody { background: $surface; }
    QScrollBar:vertical { background: $field; width: 11px; margin: 0; }
    QScrollBar::handle:vertical { background: $border; border-radius: 4px; min-height: 24px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QMenu { border: 1px solid $border; padding: 5px; }
    QMenu::item { padding: 6px 14px; }
    QMenu::item:selected { background: $selected; }
    QStatusBar { color: $muted; padding: 2px 13px 4px; }
    QStatusBar::item { border: none; }
    QToolTip { color: $ink; background: $surface; border: 1px solid $border; padding: 5px; }
    QProgressBar { background: $surface; border: 1px solid $border; border-radius: 8px; text-align: center; }
    QProgressBar::chunk { background: $selected; border-radius: 7px; }
    QWidget:disabled { color: $disabled; }
    """
    for token, color in palette.items():
        style = style.replace("$" + token + ";", color + ";")
    return style


@lru_cache(maxsize=1)
def load_display_font(resources):
    return QFontDatabase.addApplicationFont(str(resources / "resources/fonts/Nunito.ttf"))


@lru_cache(maxsize=40)
def tool_icon(kind, color, size=24):
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.scale(size / 24, size / 24)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 1.65)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)

    def line(*points):
        painter.drawPolyline([QPointF(x, y) for x, y in points])

    def rect(x, y, width, height):
        painter.drawRoundedRect(QRectF(x, y, width, height), 2, 2)

    def circle(x, y, radius):
        painter.drawEllipse(QPointF(x, y), radius, radius)

    if kind == "home":
        line((3, 11), (12, 4), (21, 11))
        line((5, 10), (5, 20), (10, 20), (10, 15), (14, 15), (14, 20), (19, 20), (19, 10))
    elif kind == "sun":
        circle(12, 12, 4)
        for _ in range(8):
            line((12, 3), (12, 5))
            painter.translate(12, 12)
            painter.rotate(45)
            painter.translate(-12, -12)
    elif kind == "moon":
        path = QPainterPath(QPointF(11, 3))
        path.cubicTo(1, 4, 1, 21, 12, 21)
        path.cubicTo(17, 21, 20, 18, 21, 14)
        path.cubicTo(13, 18, 6, 11, 11, 3)
        painter.drawPath(path)
    elif kind in {"rotate-left", "rotate-right"}:
        if kind == "rotate-left":
            painter.translate(24, 0)
            painter.scale(-1, 1)
        painter.drawArc(QRectF(4, 4, 16, 16), 45 * 16, 275 * 16)
        line((20, 3), (20, 8), (15, 8))
    elif kind == "blank":
        line((5, 3), (15, 3), (19, 7), (19, 21), (5, 21), (5, 3))
        line((15, 3), (15, 7), (19, 7))
        line((12, 10), (12, 17))
        line((8.5, 13.5), (15.5, 13.5))
    elif kind == "reverse":
        line((4, 7), (20, 7), (16, 3))
        line((20, 17), (4, 17), (8, 21))
    elif kind == "organize":
        line((8, 3), (21, 3), (21, 16))
        rect(3, 7, 14, 14)
        line((7, 12), (13, 12))
        line((7, 16), (13, 16))
    elif kind in {"up", "down", "previous", "next"}:
        angle = {"up": 0, "down": 180, "previous": 270, "next": 90}[kind]
        painter.translate(12, 12)
        painter.rotate(angle)
        painter.translate(-12, -12)
        line((7, 14), (12, 9), (17, 14))
    elif kind in {"undo", "redo"}:
        if kind == "redo":
            painter.translate(24, 0)
            painter.scale(-1, 1)
        line((8, 5), (3, 10), (8, 15))
        path = QPainterPath(QPointF(3, 10))
        path.lineTo(14, 10)
        path.cubicTo(18, 10, 21, 12, 21, 18)
        painter.drawPath(path)
    elif kind == "delete":
        line((3, 6), (21, 6))
        line((9, 6), (9, 3), (15, 3), (15, 6))
        line((5, 6), (6, 21), (18, 21), (19, 6))
        line((10, 10), (10, 17))
        line((14, 10), (14, 17))
    elif kind == "folder":
        line((3, 18), (3, 6), (10, 6), (12, 8), (19, 8), (19, 11))
        line((3, 18), (6, 11), (22, 11), (19, 18), (3, 18))
    elif kind == "save":
        line((4, 4), (17, 4), (20, 7), (20, 20), (4, 20), (4, 4))
        line((8, 4), (8, 9), (16, 9), (16, 4))
        rect(8, 13, 8, 7)
    elif kind == "export":
        line((4, 15), (4, 20), (20, 20), (20, 15))
        line((12, 3), (12, 15))
        line((8, 11), (12, 15), (16, 11))
    elif kind == "invert":
        rect(3, 3, 7, 7)
        rect(14, 14, 7, 7)
        line((14, 6), (21, 6))
        line((3, 17), (10, 17))
    elif kind == "range":
        line((7, 4), (4, 4), (4, 20), (7, 20))
        line((17, 4), (20, 4), (20, 20), (17, 20))
        line((8, 12), (16, 12))
    elif kind == "close":
        line((6, 6), (18, 18))
        line((18, 6), (6, 18))
    elif kind == "fit-page":
        rect(8, 6, 8, 12)
        for x, y, dx, dy in ((3, 3, 4, 4), (21, 3, -4, 4), (3, 21, 4, -4), (21, 21, -4, -4)):
            line((x + dx, y), (x, y), (x, y + dy))
    elif kind == "fit-width":
        line((3, 5), (3, 19))
        line((21, 5), (21, 19))
        line((5, 12), (19, 12))
        line((9, 8), (5, 12), (9, 16))
        line((15, 8), (19, 12), (15, 16))
    elif kind == "pan":
        for _ in range(4):
            line((8, 7), (12, 3), (16, 7))
            line((12, 3), (12, 12))
            painter.translate(12, 12)
            painter.rotate(90)
            painter.translate(-12, -12)
    elif kind == "merge":
        line((4, 16), (4, 4), (15, 4))
        rect(8, 8, 12, 12)
        line((14, 11.5), (14, 16.5))
        line((11.5, 14), (16.5, 14))
    elif kind == "split":
        rect(5, 3, 14, 18)
        for x in (7.5, 11.5, 15.5):
            line((x, 12), (x + 1, 12))
        line((8, 7), (15, 7))
        line((8, 17), (15, 17))
    elif kind == "extract":
        line((8, 20), (5, 20), (5, 4), (17, 4), (17, 10))
        line((10, 15), (21, 15))
        line((17, 11), (21, 15), (17, 19))
    elif kind == "image":
        rect(3.5, 4.5, 17, 15)
        circle(8.5, 9, 1.45)
        line((4, 17), (9, 12.5), (12, 15), (15.5, 10.5), (20, 16))
    elif kind == "edit":
        line((11, 19), (4, 19), (4, 4), (17, 4), (17, 7))
        line((10, 16), (10, 20), (14, 20), (21, 12), (17, 8), (10, 16))
        line((15, 10), (19, 14))
    elif kind == "settings":
        for y, knob in ((5, 9), (12, 15), (19, 10)):
            line((4, y), (knob - 2, y))
            line((knob + 2, y), (20, y))
            circle(knob, y, 2)
    elif kind == "about":
        circle(12, 12, 8)
        circle(12, 8.1, 0.45)
        line((12, 11), (12, 16))
    else:
        rect(5, 3, 14, 18)
        line((8.5, 8), (15.5, 8))
        line((8.5, 12), (15.5, 12))
        line((8.5, 16), (12.5, 16))
    painter.end()
    return QIcon(pixmap)


def action_button(kind, label, *, primary=False):
    color = LIGHT["on_primary"] if primary else LIGHT["primary"]
    button = QPushButton(tool_icon(kind, color), label)
    button.setProperty("iconKind", kind)
    button.setProperty("primary", primary)
    return button


def icon_button(kind, label):
    button = action_button(kind, "")
    button.setProperty("iconOnly", True)
    button.setFixedWidth(36)
    button.setIconSize(QSize(20, 20))
    button.setToolTip(label)
    button.setAccessibleName(label)
    return button


class Mascot(QWidget):
    def __init__(self, image):
        super().__init__()
        self.setObjectName("Mascot")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setMinimumSize(220, 218)
        self.setMaximumWidth(340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.pixmap = QPixmap(str(image))
        self.backing = QColor(LIGHT["art"])

    def paintEvent(self, _event):
        if self.pixmap.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        side = min(self.width() - 8, self.height() - 4, 298)
        left, top = (self.width() - side) / 2, (self.height() - side) / 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.backing)
        painter.drawEllipse(QRectF(left + side * 0.09, top + side * 0.07, side * 0.84, side * 0.87))
        painter.drawPixmap(QRectF(left, top, side, side), self.pixmap, QRectF(self.pixmap.rect()))


class ToolCard(QPushButton):
    def __init__(self, title, description, kind, tone, *, featured=False):
        super().__init__()
        self.setObjectName("ToolCard")
        self.setProperty("featured", featured)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumHeight(103)
        self.kind = kind
        self.icon_tile = QLabel()
        self.icon_tile.setObjectName("ToolIcon")
        self.icon_tile.setProperty("tone", tone)
        self.icon_tile.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_tile.setFixedSize(41, 41)
        self.title = QLabel(title)
        self.title.setObjectName("ToolTitle")
        self.title.setWordWrap(True)
        self.description = QLabel(description)
        self.description.setObjectName("ToolDescription")
        self.description.setWordWrap(True)
        for child in (self.icon_tile, self.title, self.description):
            child.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(13, 11, 12, 11)
        layout.setSpacing(11)
        layout.addWidget(self.icon_tile)
        text = QVBoxLayout()
        text.setSpacing(3)
        text.addStretch()
        text.addWidget(self.title)
        text.addWidget(self.description)
        text.addStretch()
        layout.addLayout(text, 1)

    def set_icon_color(self, color):
        self.icon_tile.setPixmap(tool_icon(self.kind, color).pixmap(24, 24))

    def refresh_accessibility(self):
        self.setAccessibleName(self.title.text())
        self.setAccessibleDescription(self.description.text())

    def matches(self, query):
        return query in f"{self.title.text()} {self.description.text()}".casefold()
