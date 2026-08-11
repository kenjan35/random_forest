"""
Petit utilitaire pour donner un curseur "main" (pointeur) aux boutons
cliquables. La propriété "cursor" des feuilles de style Qt (QSS) est peu
fiable selon les versions (avertissement "Unknown property cursor" et
absence d'effet) -- on passe donc par setCursor() en Python, qui fonctionne
de façon garantie.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor


def apply_pointer_cursor(button):
    """Applique le curseur adapté à l'état actuel du bouton (à appeler une
    fois, à la création)."""
    button.setCursor(QCursor(
        Qt.CursorShape.PointingHandCursor if button.isEnabled() else Qt.CursorShape.ArrowCursor
    ))


def set_button_enabled(button, enabled):
    """
    À utiliser à la place de button.setEnabled(...) pour tout bouton passé à
    apply_pointer_cursor : met à jour l'état ACTIVÉ/DÉSACTIVÉ (ce qui pilote
    aussi le style grisé défini dans QPushButton:disabled) ET le curseur en
    une seule fois, de façon explicite et fiable.
    """
    button.setEnabled(enabled)
    button.setCursor(QCursor(
        Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
    ))