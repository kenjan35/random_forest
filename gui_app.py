"""
Interface desktop pour le projet de détection de vol de carburant.

Lancement (depuis la racine du projet, là où se trouvent main.py et src/) :
    python gui_app.py

Dépendances (en plus de celles déjà utilisées par le projet) :
    pip install PySide6 matplotlib
"""

import sys

from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow
from gui.style import STYLESHEET


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
