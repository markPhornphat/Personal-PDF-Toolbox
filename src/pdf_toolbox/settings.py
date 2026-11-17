from pathlib import Path

from PySide6.QtCore import QSettings, QStandardPaths
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from .localization import Choice, ask_text, tr
from .updater import Credentials, UpdateError

DARK = """
QWidget { background: #151c26; color: #e5edf6; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QListWidget, QGraphicsView, QPushButton {
    background: #202c3b; border: 1px solid #3b5066; border-radius: 7px; padding: 5px; }
QPushButton:hover { background: #2c3a4c; }
QWidget:disabled { color: #8290a3; }
QListWidget::item:selected { background: #274c72; color: #ffffff; }
"""
LIGHT = """
QWidget { background: #f6f8fc; color: #142438; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QListWidget, QGraphicsView, QPushButton {
    background: #ffffff; border: 1px solid #c7d3e2; border-radius: 7px; padding: 5px; }
QPushButton:hover { background: #eaf4ff; }
QWidget:disabled { color: #778597; }
QListWidget::item:selected { background: #d8eaff; color: #173b66; }
"""
COMMON = """
QWidget { font-family: "Segoe UI"; font-size: 13px; }
QPushButton { min-height: 24px; padding: 5px 12px; text-align: center; }
QPushButton[primary="true"] { background: #075db4; border-color: #075db4; color: white; }
QPushButton[primary="true"]:hover { background: #064d95; }
QPushButton[primary="true"]:disabled { background: #59728b; border-color: #59728b; }
QLabel#Heading { font-size: 26px; font-weight: 650; }
QLabel#Brand { font-size: 24px; font-weight: 700; }
QLabel#Section { font-size: 17px; font-weight: 650; }
QPushButton#ToolCard { font-size: 15px; text-align: left; min-height: 55px; padding: 10px; }
QFrame#DropArea { border: 2px dashed #679acc; border-radius: 12px; }
QFrame#DropArea[dragging="true"] { border: 3px solid #1677cf; }
"""


def data_path() -> Path:
    return (
        Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation))
        / "PDF Toolbox"
    )


def preferences():
    return QSettings(str(data_path() / "settings.ini"), QSettings.Format.IniFormat)


class Settings(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.prefs = window.prefs
        form = QFormLayout(self)
        self.language = self.combo(
            form, "Language", "language", ["English", "ไทย"], "English", window.translate
        )
        self.theme = self.combo(
            form, "Theme", "theme", ["System", "Light", "Dark"], "System", window.apply_theme
        )
        self.folder = QPushButton(self.prefs.value("folder", "Choose folder…"))
        self.folder.clicked.connect(self.choose_folder)
        form.addRow("Default output folder", self.folder)
        self.spin(form, "Default image DPI", "dpi", 1, 2400, 200)
        self.spin(form, "JPG quality", "quality", 1, 100, 90)
        self.automatic = QCheckBox("Check GitHub for updates in the background")
        self.automatic.setChecked(self.prefs.value("auto_updates", False, type=bool))
        self.automatic.toggled.connect(self.toggle_updates)
        form.addRow("Software updates", self.automatic)
        self.spin(form, "Check interval (hours)", "interval", 1, 168, 24)
        self.check = QPushButton("Check for updates")
        self.check.clicked.connect(lambda: window.check_updates(manual=True))
        form.addRow(self.check)
        self.status = QLineEdit(self.prefs.value("update_status", "No update checks yet"))
        self.status.setReadOnly(True)
        form.addRow("Last check", self.status)
        credential = QPushButton("Manage GitHub credential…")
        credential.clicked.connect(self.manage_credential)
        form.addRow(credential)
        credential.setVisible(bool(window.update_config and window.update_config.private))
        self.button(form, "Clear preview cache", window.clear_cache)
        self.button(form, "Reset preferences", self.reset)
        self.button(form, "About", window.about)

    def combo(self, form, label, key, values, default, callback):
        box = Choice()
        box.addItems(values)
        box.setCurrentText(self.prefs.value(key, default))
        box.currentIndexChanged.connect(
            lambda index: (self.prefs.setValue(key, box.itemData(index)), callback())
        )
        form.addRow(label, box)
        return box

    def spin(self, form, label, key, minimum, maximum, default):
        box = QSpinBox()
        box.setRange(minimum, maximum)
        box.setValue(self.prefs.value(key, default, type=int))
        box.valueChanged.connect(lambda value: self.prefs.setValue(key, value))
        form.addRow(label, box)

    def button(self, form, label, slot):
        button = QPushButton(label)
        button.clicked.connect(slot)
        form.addRow(button)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, tr(self, "Default output folder"), self.prefs.value("folder", "")
        )
        if folder:
            self.prefs.setValue("folder", folder)
            self.folder.setText(folder)

    def toggle_updates(self, enabled):
        if enabled and not self.window.confirm(
            "Enable update checks?",
            "PDF Toolbox will contact the configured GitHub repository to check for new "
            "installers. It sends no document or clipboard information.",
        ):
            self.automatic.blockSignals(True)
            self.automatic.setChecked(False)
            self.automatic.blockSignals(False)
            return
        self.prefs.setValue("auto_updates", enabled)
        if enabled:
            self.window.check_updates(manual=False)

    def manage_credential(self):
        config = self.window.update_config
        if not config:
            return
        token, ok = ask_text(
            self,
            "GitHub update credential",
            "Paste a read-only token for the update repository. Leave blank to remove it.",
            QLineEdit.EchoMode.Password,
        )
        if ok:
            try:
                Credentials(config.repository).save(token.strip())
                self.window.notice("GitHub update credential preference saved.")
            except UpdateError as error:
                self.window.alert(str(error))

    def reset(self):
        if self.window.confirm("Reset preferences?", "This restores the default app preferences."):
            self.prefs.clear()
            self.language.setCurrentText("English")
            self.theme.setCurrentText("System")
            self.automatic.setChecked(False)
            self.folder.setText(tr(self, "Choose folder…"))
            self.window.update_status("No update checks yet")
