"""
Interface desktop pour le projet de détection de vol de carburant.

Lancement (depuis la racine du projet, là où se trouvent main.py et src/) :
    python gui_app.py

Dépendances (en plus de celles déjà utilisées par le projet) :
    pip install PySide6 matplotlib
"""

# First version of the GUI, not used anymore. The current GUI is in gui/main_window.py and launched from main.py.
# import sys

# from PySide6.QtWidgets import QApplication

# from gui.main_window import MainWindow
# from gui.style import STYLESHEET


# def main():
#     app = QApplication(sys.argv)
#     app.setStyleSheet(STYLESHEET)

#     window = MainWindow()
#     window.show()

#     sys.exit(app.exec())


# if __name__ == "__main__":
#     main()

"""
Interface desktop pour le projet de détection de vol de carburant.

Lancement (depuis la racine du projet, là où se trouvent main.py et src/) :
    python gui_app.py

Dépendances (en plus de celles déjà utilisées par le projet) :
    pip install PySide6 matplotlib
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