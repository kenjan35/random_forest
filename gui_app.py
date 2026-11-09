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
    _set_windows_app_id()
    app = QApplication(sys.argv)
    _configure_app(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


def _set_windows_app_id():
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FuelTheftDetector.App.1")
    except Exception:
        pass


def _configure_app(app):
    app.setStyleSheet(STYLESHEET)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))


if __name__ == "__main__":
    main()