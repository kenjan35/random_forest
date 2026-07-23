import os

from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox

from gui.single_file_tab import SingleFileTab
from gui.batch_scan_tab import BatchScanTab

MODEL_PATH = os.path.join("model", "random_forest.pkl")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Détection de vol de carburant")
        self.resize(1200, 750)

        tabs = QTabWidget()
        tabs.addTab(SingleFileTab(), "Fichier unique")
        tabs.addTab(BatchScanTab(), "Scanner un dossier")
        self.setCentralWidget(tabs)

        if not os.path.exists(MODEL_PATH):
            QMessageBox.warning(
                self,
                "Modèle non trouvé",
                f"'{MODEL_PATH}' est introuvable.\n\n"
                "Lancez d'abord `python main.py` à la racine du projet pour "
                "entraîner et sauvegarder le modèle avant d'utiliser cette interface.",
            )
