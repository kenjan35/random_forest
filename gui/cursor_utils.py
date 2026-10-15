"""
Petit utilitaire pour donner un curseur "main" (pointeur) aux boutons
cliquables. La propriété "cursor" des feuilles de style Qt (QSS) est peu
fiable selon les versions (avertissement "Unknown property cursor" et
absence d'effet) -- on passe donc par setCursor() en Python, qui fonctionne
de façon garantie.
"""

import os
import re

from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import QByteArray, QTimer
from PySide6.QtGui import QCursor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


SPINNER_ICON = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "icons", "spinner.svg"
)
_spinner_svg = None
_spinner_frames = {}


def _get_spinner_frames(size):
    global _spinner_svg
    if size in _spinner_frames:
        return _spinner_frames[size]
    if _spinner_svg is None:
        with open(SPINNER_ICON, "r", encoding="utf-8") as file:
            _spinner_svg = file.read()
    svg_without_animation = re.sub(r"<animate\b[^>]*></animate>", "", _spinner_svg)
    rect_pattern = re.compile(r"<rect\b([^>]*)>")
    frames = []
    for active_index in range(12):
        rect_index = 0

        def replace_rect(match):
            nonlocal rect_index
            opacity = "1" if rect_index == active_index else "0.2"
            rect_index += 1
            return f'<rect{match.group(1)} opacity="{opacity}">'

        frame_svg = rect_pattern.sub(replace_rect, svg_without_animation)
        renderer = QSvgRenderer(QByteArray(frame_svg.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        frames.append(QIcon(pixmap))
    _spinner_frames[size] = frames
    return frames


def _advance_spinner(button):
    frames = _get_spinner_frames(button._spinner_size)
    button._spinner_frame = (button._spinner_frame + 1) % len(frames)
    button.setIcon(frames[button._spinner_frame])


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


def set_button_busy(button, busy):
    """Anime le spinner pendant une action sans changer le texte du bouton."""
    if not hasattr(button, "_idle_icon"):
        button._idle_icon = button.icon()
        button._idle_icon_size = button.iconSize()
        button._spinner_size = 26
        button._spinner_timer = QTimer(button)
        button._spinner_timer.timeout.connect(lambda: _advance_spinner(button))
    if busy:
        try:
            _get_spinner_frames(button._spinner_size)
        except OSError:
            return  # icône du spinner absente : on garde le bouton tel quel
        button._spinner_frame = -1
        button.setIconSize(QSize(button._spinner_size, button._spinner_size))
        _advance_spinner(button)
        button._spinner_timer.start(80)
    else:
        button._spinner_timer.stop()
        button.setIcon(button._idle_icon)
        button.setIconSize(button._idle_icon_size)