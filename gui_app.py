"""
Interface desktop pour le projet de détection de vol de carburant.

Lancement (depuis la racine du projet, là où se trouvent main.py et src/) :
    python gui_app.py

Dépendances : voir requirements-gui.txt (installées par installer.bat)
"""

import sys
import os

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from gui.main_window import MainWindow
from gui.style import STYLESHEET

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")


def main():
    # Tous les chemins relatifs (assets/, model/, data/) partent de la racine du
    # projet, même si l'application est lancée depuis un autre dossier.
    os.chdir(BASE_DIR)

    # Sous Windows, lancé via pythonw.exe (pas un .exe compilé), la barre
    # des tâches affiche souvent l'icône de Python au lieu de la nôtre tant
    # que le processus n'a pas son propre identifiant d'application. Sans
    # ça, setWindowIcon() ne suffit pas toujours pour la barre des tâches
    # (il fonctionne déjà bien pour la barre de titre).
    if sys.platform == "win32":
        import ctypes
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "FuelTheftDetector.App.1"
            )
        except Exception:
            pass  # non bloquant : au pire l'icone par defaut de Python reste affichee

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()