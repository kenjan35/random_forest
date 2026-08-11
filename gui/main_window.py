import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QPushButton, QApplication,
    QWidget, QHBoxLayout
)

from gui.single_file_tab import SingleFileTab
from gui.batch_scan_tab import BatchScanTab
from gui.chart import FuelChart
from gui.style import DARK_STYLESHEET, LIGHT_STYLESHEET
from gui.cursor_utils import apply_pointer_cursor

MODEL_PATH = os.path.join("model", "random_forest.pkl")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Détection de vol de carburant")
        self.resize(1200, 750)
        self.dark_mode = True

        tabs = QTabWidget()
        tabs.addTab(SingleFileTab(), "Fichier unique")
        tabs.addTab(BatchScanTab(), "Scanner un dossier")
        tabs.tabBar().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.theme_btn = QPushButton("☀️  Mode clair")
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setFixedWidth(185)
        self.theme_btn.clicked.connect(self.toggle_theme)
        apply_pointer_cursor(self.theme_btn)

        theme_btn_container = QWidget()
        theme_btn_layout = QHBoxLayout(theme_btn_container)
        theme_btn_layout.setContentsMargins(0, 4, 12, 4)  # marge, surtout à droite, pour ne pas coller au bord
        theme_btn_layout.addWidget(self.theme_btn)
        tabs.setCornerWidget(theme_btn_container, Qt.Corner.TopRightCorner)

        self.setCentralWidget(tabs)

        if not os.path.exists(MODEL_PATH):
            QMessageBox.warning(
                self,
                "Modèle non trouvé",
                f"'{MODEL_PATH}' est introuvable.\n\n"
                "Lancez d'abord `python main.py` à la racine du projet pour "
                "entraîner et sauvegarder le modèle avant d'utiliser cette interface.",
            )

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode

        app = QApplication.instance()
        app.setStyleSheet(DARK_STYLESHEET if self.dark_mode else LIGHT_STYLESHEET)

        self.theme_btn.setText("☀️  Mode clair" if self.dark_mode else "🌙  Mode sombre")

        for chart in self.findChildren(FuelChart):
            chart.set_theme(self.dark_mode)