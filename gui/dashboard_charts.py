"""
Dessin des graphiques du Dashboard, séparé du widget Qt pour pouvoir être
testé (et prévisualisé) sans interface. Chaque fonction reçoit des axes
matplotlib déjà créés, les données brutes de site_history et un thème.
"""

from gui.dashboard_charts_daily_utils import draw_daily
from gui.dashboard_charts_hour_utils import draw_hours

# Une seule teinte (celle de l'application), déclinée en accent / atténué.
THEMES = {
    "light": dict(
        surface="#ffffff", text="#0f172a", muted="#64748b", grid="#e2e8f0",
        mark="#1690bd", mark_soft="#a9dcf1", edge="#ffffff",
    ),
    "dark": dict(
        surface="#45454a", text="#e6e8ec", muted="#aeb5c0", grid="#56575e",
        mark="#3fbde9", mark_soft="#2f6e88", edge="#45454a",
    ),
}

FONT_SIZE = 9


def theme(is_dark):
    return THEMES["dark" if is_dark else "light"]
