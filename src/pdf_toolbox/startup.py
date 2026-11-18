"""Display the splash before importing the PDF and Word tools."""

import sys
from pathlib import Path

from PySide6.QtCore import QRectF, QStandardPaths, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen


def launch():
    application = QApplication(sys.argv)
    application.setApplicationName("PDF Toolbox")
    application.setStyle("Fusion")
    smoke = "--smoke-test" in sys.argv
    if smoke:
        QStandardPaths.setTestModeEnabled(True)
    splash = None if smoke else show_splash(application)
    try:
        from .app import main

        return main(application, splash)
    finally:
        if splash is not None:
            splash.close()


def show_splash(application):
    from .appearance import DARK, LIGHT, load_display_font

    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    load_display_font(root)
    palette = DARK if application.styleHints().colorScheme() == Qt.ColorScheme.Dark else LIGHT
    screen = application.primaryScreen()
    ratio = screen.devicePixelRatio() if screen else 1.0
    canvas = QPixmap(round(340 * ratio), round(228 * ratio))
    canvas.setDevicePixelRatio(ratio)
    canvas.fill(QColor(palette["background"]))
    with QPainter(canvas) as painter:
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(palette["art"]))
        painter.drawEllipse(QRectF(114, 19, 112, 112))
        mascot = QPixmap(str(root / "resources/paper-dog.png"))
        painter.drawPixmap(QRectF(121, 24, 98, 98), mascot, QRectF(mascot.rect()))
        painter.setPen(QColor(palette["ink"]))
        painter.setFont(QFont("Nunito", 22, QFont.Weight.Bold))
        painter.drawText(QRectF(0, 137, 340, 39), Qt.AlignmentFlag.AlignCenter, "PDF Toolbox")
        painter.setPen(QColor(palette["muted"]))
        painter.setFont(QFont("Nunito", 11))
        painter.drawText(QRectF(0, 181, 340, 25), Qt.AlignmentFlag.AlignCenter, "Loading…")
    splash = QSplashScreen(canvas)
    splash.setWindowTitle("Loading PDF Toolbox")
    splash.show()
    application.processEvents()
    return splash
