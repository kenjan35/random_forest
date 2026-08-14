# """
# Graphique du niveau de carburant, avec les périodes suspectes surlignées
# et un bandeau d'état du générateur (Actif/Inactif) en dessous.
# S'adapte au thème clair/sombre de l'application.
# """

# import numpy as np

# import matplotlib
# matplotlib.use("QtAgg")
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure

# FUEL_COLOR = "#1caae2"
# ALERT_COLOR = "#ef4444"
# ACTIVE_COLOR = "#22c55e"
# INACTIVE_COLOR = "#94a3b8"

# THEMES = {
#     "dark": dict(figure_bg="#22252c", axes_bg="#22252c", text="#e6e8ec", grid="#3a3e48"),
#     "light": dict(figure_bg="#ffffff", axes_bg="#ffffff", text="#0f172a", grid="#cbd5e1"),
# }


# class FuelChart(FigureCanvas):
#     def __init__(self, parent=None):
#         self.fig = Figure(figsize=(6, 4), dpi=100, tight_layout=True)
#         super().__init__(self.fig)
#         self.setParent(parent)
#         self.ax_fuel = None
#         self.ax_status = None
#         self._theme = THEMES["dark"]
#         self._last_result = None
#         self._build_axes()

#     def set_theme(self, is_dark):
#         self._theme = THEMES["dark"] if is_dark else THEMES["light"]
#         if self._last_result is not None:
#             self.plot(self._last_result)
#         else:
#             self.clear()

#     def _build_axes(self):
#         self.fig.clear()
#         self.fig.patch.set_facecolor(self._theme["figure_bg"])
#         gs = self.fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.08)
#         self.ax_fuel = self.fig.add_subplot(gs[0])
#         self.ax_status = self.fig.add_subplot(gs[1], sharex=self.ax_fuel)
#         for ax in (self.ax_fuel, self.ax_status):
#             ax.set_facecolor(self._theme["axes_bg"])
#             ax.tick_params(colors=self._theme["text"])
#             for spine in ax.spines.values():
#                 spine.set_color(self._theme["grid"])

#     def clear(self):
#         self._last_result = None
#         self._build_axes()
#         self.draw()

#     def plot(self, result):
#         self._last_result = result
#         self._build_axes()
#         fuel = result["fuel"]
#         active = result["active"]
#         x = np.arange(len(fuel))
#         text_color = self._theme["text"]

#         self.ax_fuel.plot(x, fuel, color=FUEL_COLOR, linewidth=1.2, label="Carburant (L)")
#         for ev in result["events"]:
#             self.ax_fuel.axvspan(ev["row_start"], ev["row_end"], color=ALERT_COLOR, alpha=0.25)

#         title = result["filename"]
#         if result["has_theft"]:
#             title += f"  —  {result['n_events']} période(s) suspecte(s)"
#         else:
#             title += "  —  aucun vol détecté"
#         self.ax_fuel.set_title(title, fontsize=11, fontweight="bold", color=text_color)
#         self.ax_fuel.set_ylabel("Litres", color=text_color)
#         self.ax_fuel.tick_params(labelbottom=False)
#         self.ax_fuel.grid(alpha=0.25, color=self._theme["grid"])

#         # bandeau d'état du générateur, simplifié si trop de bascules pour rester lisible
#         self.ax_status.fill_between(
#             x, 0, 1, where=active, color=ACTIVE_COLOR, step="mid", alpha=0.6, label="Actif"
#         )
#         self.ax_status.fill_between(
#             x, 0, 1, where=~active, color=INACTIVE_COLOR, step="mid", alpha=0.6, label="Inactif"
#         )
#         self.ax_status.set_yticks([])
#         self.ax_status.set_xlabel("Relevé (index)", color=text_color)

#         self.draw()

# First version with zoom/pan and reset button, using a QWidget wrapper around the FigureCanvas.
# """
# Graphique du niveau de carburant, avec les périodes suspectes surlignées
# et un bandeau d'état du générateur (Actif/Inactif) en dessous.
# S'adapte au thème clair/sombre de l'application.

# Interaction :
#   - molette      : zoom, centré sur la position du curseur
#   - clic-glisser : déplacement horizontal (une fois zoomé)
#   - double-clic, ou bouton "Réinitialiser le zoom" : retour à la vue complète
# L'échelle des litres se réajuste automatiquement aux données visibles.
# """

# import numpy as np

# import matplotlib
# matplotlib.use("QtAgg")
# from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.figure import Figure

# from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

# from gui.cursor_utils import apply_pointer_cursor, set_button_enabled

# FUEL_COLOR = "#1caae2"
# ALERT_COLOR = "#ef4444"
# ACTIVE_COLOR = "#22c55e"
# INACTIVE_COLOR = "#94a3b8"

# THEMES = {
#     "dark": dict(figure_bg="#22252c", axes_bg="#22252c", text="#e6e8ec", grid="#3a3e48"),
#     "light": dict(figure_bg="#ffffff", axes_bg="#ffffff", text="#0f172a", grid="#cbd5e1"),
# }

# # --- zoom / pan ---
# ZOOM_SCALE = 1.2        # facteur applique a chaque cran de molette
# Y_PADDING_RATIO = 0.08  # marge au-dessus/en-dessous des donnees visibles


# def _clamp_xlim(new_min, new_max, full_xlim, eps=1e-9):
#     """Ramène (new_min, new_max) à l'intérieur de full_xlim, sans jamais
#     dépasser sa largeur totale (tolérance eps pour l'arrondi flottant)."""
#     full_min, full_max = full_xlim
#     full_width = full_max - full_min
#     width = new_max - new_min
#     if width >= full_width - eps:
#         return full_min, full_max
#     if new_min < full_min:
#         new_min, new_max = full_min, full_min + width
#     if new_max > full_max:
#         new_max, new_min = full_max, full_max - width
#     return new_min, new_max


# def _zoomed_xlim(x_min, x_max, xdata, factor, full_xlim):
#     """Nouvelles limites X après un zoom de facteur `factor` centré sur
#     `xdata` (position du curseur) ; factor < 1 rapproche, > 1 éloigne."""
#     width = x_max - x_min
#     if width <= 0:
#         return x_min, x_max
#     full_min, full_max = full_xlim
#     new_width = min(width * factor, full_max - full_min)
#     if xdata is None:
#         xdata = (x_min + x_max) / 2
#     left_ratio = (xdata - x_min) / width
#     new_min = xdata - left_ratio * new_width
#     new_max = new_min + new_width
#     return _clamp_xlim(new_min, new_max, full_xlim)


# def _panned_xlim(start_xlim, dx, full_xlim):
#     """Limites X après un déplacement de `dx` (mêmes unités que l'axe X)
#     depuis `start_xlim`."""
#     x_min0, x_max0 = start_xlim
#     return _clamp_xlim(x_min0 + dx, x_max0 + dx, full_xlim)


# def _rescaled_ylim(fuel, x_min, x_max, padding_ratio=Y_PADDING_RATIO):
#     """Ajuste l'échelle Y au minimum/maximum du carburant réellement
#     visible dans la fenêtre [x_min, x_max], avec une petite marge."""
#     lo = max(0, int(np.floor(x_min)))
#     hi = min(len(fuel) - 1, int(np.ceil(x_max)))
#     if lo > hi:
#         lo, hi = hi, lo
#     visible = fuel[lo:hi + 1]
#     if len(visible) == 0:
#         return None
#     y_min, y_max = float(visible.min()), float(visible.max())
#     if y_min == y_max:
#         y_min -= 1.0
#         y_max += 1.0
#     pad = (y_max - y_min) * padding_ratio
#     return y_min - pad, y_max + pad

# class FuelChart(QWidget):
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.fig = Figure(figsize=(6, 4), dpi=100, tight_layout=True)
#         self.canvas = FigureCanvas(self.fig)
#         self.ax_fuel = None
#         self.ax_status = None
#         self._theme = THEMES["dark"]
#         self._last_result = None
#         self._fuel = None
#         self._full_xlim = None
#         self._pan_start = None

#         self.reset_btn = QPushButton("Réinitialiser le zoom")
#         self.reset_btn.setObjectName("secondary")
#         self.reset_btn.clicked.connect(self.reset_zoom)
#         apply_pointer_cursor(self.reset_btn)
#         set_button_enabled(self.reset_btn, False)

#         layout = QVBoxLayout(self)
#         layout.setContentsMargins(0, 0, 0, 0)
#         layout.setSpacing(4)
#         bar = QHBoxLayout()
#         bar.addStretch(1)
#         bar.addWidget(self.reset_btn)
#         layout.addLayout(bar)
#         layout.addWidget(self.canvas)

#         self._build_axes()

#         self.canvas.mpl_connect("scroll_event", self._on_scroll)
#         self.canvas.mpl_connect("button_press_event", self._on_button_press)
#         self.canvas.mpl_connect("motion_notify_event", self._on_motion)
#         self.canvas.mpl_connect("button_release_event", self._on_button_release)

#     def set_theme(self, is_dark):
#         self._theme = THEMES["dark"] if is_dark else THEMES["light"]
#         if self._last_result is not None:
#             self.plot(self._last_result)
#         else:
#             self.clear()

#     def _build_axes(self):
#         self.fig.clear()
#         self.fig.patch.set_facecolor(self._theme["figure_bg"])
#         gs = self.fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.08)
#         self.ax_fuel = self.fig.add_subplot(gs[0])
#         self.ax_status = self.fig.add_subplot(gs[1], sharex=self.ax_fuel)
#         for ax in (self.ax_fuel, self.ax_status):
#             ax.set_facecolor(self._theme["axes_bg"])
#             ax.tick_params(colors=self._theme["text"])
#             for spine in ax.spines.values():
#                 spine.set_color(self._theme["grid"])

#     def clear(self):
#         self._last_result = None
#         self._fuel = None
#         self._full_xlim = None
#         self._pan_start = None
#         self._build_axes()
#         set_button_enabled(self.reset_btn, False)
#         self.canvas.draw_idle()

#     def plot(self, result):
#         self._last_result = result
#         self._build_axes()
#         fuel = result["fuel"]
#         active = result["active"]
#         x = np.arange(len(fuel))
#         text_color = self._theme["text"]

#         self.ax_fuel.plot(x, fuel, color=FUEL_COLOR, linewidth=1.2, label="Carburant (L)")
#         for ev in result["events"]:
#             self.ax_fuel.axvspan(ev["row_start"], ev["row_end"], color=ALERT_COLOR, alpha=0.25)

#         title = result["filename"]
#         if result["has_theft"]:
#             title += f"  —  {result['n_events']} période(s) suspecte(s)"
#         else:
#             title += "  —  aucun vol détecté"
#         self.ax_fuel.set_title(title, fontsize=11, fontweight="bold", color=text_color)
#         self.ax_fuel.set_ylabel("Litres", color=text_color)
#         self.ax_fuel.tick_params(labelbottom=False)
#         self.ax_fuel.grid(alpha=0.25, color=self._theme["grid"])

#         # bandeau d'état du générateur, simplifié si trop de bascules pour rester lisible
#         self.ax_status.fill_between(
#             x, 0, 1, where=active, color=ACTIVE_COLOR, step="mid", alpha=0.6, label="Actif"
#         )
#         self.ax_status.fill_between(
#             x, 0, 1, where=~active, color=INACTIVE_COLOR, step="mid", alpha=0.6, label="Inactif"
#         )
#         self.ax_status.set_yticks([])
#         self.ax_status.set_xlabel("Relevé (index)", color=text_color)

#         self._fuel = fuel
#         self._full_xlim = (0, max(len(fuel) - 1, 1))
#         self.ax_fuel.set_xlim(*self._full_xlim)
#         self._rescale_y()
#         set_button_enabled(self.reset_btn, False)
#         self.canvas.draw_idle()

#     # --- zoom / pan ---

#     def reset_zoom(self):
#         if self._full_xlim is None:
#             return
#         self.ax_fuel.set_xlim(*self._full_xlim)
#         self._rescale_y()
#         self._update_zoom_button_state()
#         self.canvas.draw_idle()

#     def _rescale_y(self):
#         if self._fuel is None:
#             return
#         x_min, x_max = self.ax_fuel.get_xlim()
#         ylim = _rescaled_ylim(self._fuel, x_min, x_max)
#         if ylim is not None:
#             self.ax_fuel.set_ylim(*ylim)

#     def _update_zoom_button_state(self):
#         if self._full_xlim is None:
#             return
#         x_min, x_max = self.ax_fuel.get_xlim()
#         full_min, full_max = self._full_xlim
#         is_zoomed = (x_min > full_min + 0.5) or (x_max < full_max - 0.5)
#         set_button_enabled(self.reset_btn, is_zoomed)

#     def _on_scroll(self, event):
#         if self._full_xlim is None or event.inaxes not in (self.ax_fuel, self.ax_status):
#             return
#         factor = (1 / ZOOM_SCALE) if event.button == "up" else ZOOM_SCALE
#         x_min, x_max = self.ax_fuel.get_xlim()
#         new_xlim = _zoomed_xlim(x_min, x_max, event.xdata, factor, self._full_xlim)
#         self.ax_fuel.set_xlim(*new_xlim)
#         self._rescale_y()
#         self._update_zoom_button_state()
#         self.canvas.draw_idle()

#     def _on_button_press(self, event):
#         if self._full_xlim is None or event.inaxes not in (self.ax_fuel, self.ax_status):
#             return
#         if event.dblclick:
#             self.reset_zoom()
#             return
#         if event.button != 1 or event.x is None:
#             return
#         self._pan_start = {"x_pixel": event.x, "xlim": self.ax_fuel.get_xlim()}

#     def _on_motion(self, event):
#         if self._pan_start is None or event.x is None:
#             return
#         bbox = self.ax_fuel.get_window_extent()
#         if bbox.width == 0:
#             return
#         x_min0, x_max0 = self._pan_start["xlim"]
#         data_per_pixel = (x_max0 - x_min0) / bbox.width
#         dx = (self._pan_start["x_pixel"] - event.x) * data_per_pixel
#         new_xlim = _panned_xlim((x_min0, x_max0), dx, self._full_xlim)
#         self.ax_fuel.set_xlim(*new_xlim)
#         self._rescale_y()
#         self.canvas.draw_idle()

#     def _on_button_release(self, event):
#         self._pan_start = None
#         self._update_zoom_button_state()

"""
Graphique du niveau de carburant, avec les périodes suspectes surlignées
et un bandeau d'état du générateur (Actif/Inactif) en dessous.
S'adapte au thème clair/sombre de l'application.

Interaction :
  - molette      : zoom, centré sur la position du curseur
  - clic-glisser : déplacement horizontal (une fois zoomé)
  - double-clic, ou bouton "Réinitialiser le zoom" : retour à la vue complète
L'échelle des litres se réajuste automatiquement aux données visibles.
"""

import numpy as np

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton

from gui.cursor_utils import apply_pointer_cursor, set_button_enabled

FUEL_COLOR = "#1caae2"
ALERT_COLOR = "#ef4444"
ACTIVE_COLOR = "#22c55e"
INACTIVE_COLOR = "#94a3b8"

THEMES = {
    "dark": dict(figure_bg="#22252c", axes_bg="#22252c", text="#e6e8ec", grid="#3a3e48"),
    "light": dict(figure_bg="#ffffff", axes_bg="#ffffff", text="#0f172a", grid="#cbd5e1"),
}

# --- zoom / pan ---
ZOOM_SCALE = 1.2           # facteur applique a chaque cran de molette
Y_PADDING_RATIO = 0.08     # marge au-dessus/en-dessous des donnees visibles
REDRAW_THROTTLE_MS = 30    # rendu reel limite a ~1 fois par 30ms pendant une rafale


def _clamp_xlim(new_min, new_max, full_xlim, eps=1e-9):
    """Ramène (new_min, new_max) à l'intérieur de full_xlim, sans jamais
    dépasser sa largeur totale (tolérance eps pour l'arrondi flottant)."""
    full_min, full_max = full_xlim
    full_width = full_max - full_min
    width = new_max - new_min
    if width >= full_width - eps:
        return full_min, full_max
    if new_min < full_min:
        new_min, new_max = full_min, full_min + width
    if new_max > full_max:
        new_max, new_min = full_max, full_max - width
    return new_min, new_max


def _zoomed_xlim(x_min, x_max, xdata, factor, full_xlim):
    """Nouvelles limites X après un zoom de facteur `factor` centré sur
    `xdata` (position du curseur) ; factor < 1 rapproche, > 1 éloigne."""
    width = x_max - x_min
    if width <= 0:
        return x_min, x_max
    full_min, full_max = full_xlim
    new_width = min(width * factor, full_max - full_min)
    if xdata is None:
        xdata = (x_min + x_max) / 2
    left_ratio = (xdata - x_min) / width
    new_min = xdata - left_ratio * new_width
    new_max = new_min + new_width
    return _clamp_xlim(new_min, new_max, full_xlim)


def _panned_xlim(start_xlim, dx, full_xlim):
    """Limites X après un déplacement de `dx` (mêmes unités que l'axe X)
    depuis `start_xlim`."""
    x_min0, x_max0 = start_xlim
    return _clamp_xlim(x_min0 + dx, x_max0 + dx, full_xlim)


def _rescaled_ylim(fuel, x_min, x_max, padding_ratio=Y_PADDING_RATIO):
    """Ajuste l'échelle Y au minimum/maximum du carburant réellement
    visible dans la fenêtre [x_min, x_max], avec une petite marge."""
    lo = max(0, int(np.floor(x_min)))
    hi = min(len(fuel) - 1, int(np.ceil(x_max)))
    if lo > hi:
        lo, hi = hi, lo
    visible = fuel[lo:hi + 1]
    if len(visible) == 0:
        return None
    y_min, y_max = float(visible.min()), float(visible.max())
    if y_min == y_max:
        y_min -= 1.0
        y_max += 1.0
    pad = (y_max - y_min) * padding_ratio
    return y_min - pad, y_max + pad


class FuelChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(figsize=(6, 4), dpi=100, tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax_fuel = None
        self.ax_status = None
        self._theme = THEMES["dark"]
        self._last_result = None
        self._fuel = None
        self._full_xlim = None
        self._pan_start = None
        self._redraw_pending = False
        self._redraw_timer = QTimer(self)
        self._redraw_timer.setSingleShot(True)
        self._redraw_timer.setInterval(REDRAW_THROTTLE_MS)
        self._redraw_timer.timeout.connect(self._on_redraw_timeout)

        self.reset_btn = QPushButton("Réinitialiser le zoom")
        self.reset_btn.setObjectName("secondary")
        self.reset_btn.clicked.connect(self.reset_zoom)
        apply_pointer_cursor(self.reset_btn)
        set_button_enabled(self.reset_btn, False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        bar = QHBoxLayout()
        bar.addStretch(1)
        bar.addWidget(self.reset_btn)
        layout.addLayout(bar)
        layout.addWidget(self.canvas)

        self._build_axes()

        self.canvas.mpl_connect("scroll_event", self._on_scroll)
        self.canvas.mpl_connect("button_press_event", self._on_button_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_release_event", self._on_button_release)

    def set_theme(self, is_dark):
        self._theme = THEMES["dark"] if is_dark else THEMES["light"]
        if self._last_result is not None:
            self.plot(self._last_result)
        else:
            self.clear()

    def _build_axes(self):
        self.fig.clear()
        self.fig.patch.set_facecolor(self._theme["figure_bg"])
        gs = self.fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.08)
        self.ax_fuel = self.fig.add_subplot(gs[0])
        self.ax_status = self.fig.add_subplot(gs[1], sharex=self.ax_fuel)
        for ax in (self.ax_fuel, self.ax_status):
            ax.set_facecolor(self._theme["axes_bg"])
            ax.tick_params(colors=self._theme["text"])
            for spine in ax.spines.values():
                spine.set_color(self._theme["grid"])

    def clear(self):
        self._last_result = None
        self._fuel = None
        self._full_xlim = None
        self._pan_start = None
        self._build_axes()
        set_button_enabled(self.reset_btn, False)
        self.canvas.draw_idle()

    def plot(self, result):
        self._last_result = result
        self._build_axes()
        fuel = result["fuel"]
        active = result["active"]
        x = np.arange(len(fuel))
        text_color = self._theme["text"]

        self.ax_fuel.plot(x, fuel, color=FUEL_COLOR, linewidth=1.2, label="Carburant (L)")
        for ev in result["events"]:
            self.ax_fuel.axvspan(ev["row_start"], ev["row_end"], color=ALERT_COLOR, alpha=0.25)

        title = result["filename"]
        if result["has_theft"]:
            title += f"  —  {result['n_events']} période(s) suspecte(s)"
        else:
            title += "  —  aucun vol détecté"
        self.ax_fuel.set_title(title, fontsize=11, fontweight="bold", color=text_color)
        self.ax_fuel.set_ylabel("Litres", color=text_color)
        self.ax_fuel.tick_params(labelbottom=False)
        self.ax_fuel.grid(alpha=0.25, color=self._theme["grid"])

        # bandeau d'état du générateur, simplifié si trop de bascules pour rester lisible
        self.ax_status.fill_between(
            x, 0, 1, where=active, color=ACTIVE_COLOR, step="mid", alpha=0.6, label="Actif"
        )
        self.ax_status.fill_between(
            x, 0, 1, where=~active, color=INACTIVE_COLOR, step="mid", alpha=0.6, label="Inactif"
        )
        self.ax_status.set_yticks([])
        self.ax_status.set_xlabel("Relevé (index)", color=text_color)

        self._fuel = fuel
        self._full_xlim = (0, max(len(fuel) - 1, 1))
        self.ax_fuel.set_xlim(*self._full_xlim)
        self._rescale_y()
        set_button_enabled(self.reset_btn, False)
        self.canvas.draw_idle()

    # --- zoom / pan ---

    def _request_redraw(self):
        """
        Découple la mise à jour de l'état (instantanée, à chaque événement)
        du rendu réel (coûteux, ~25-30ms sur ce graphique). Sans ça, une
        rafale de molette plus rapide que le temps de rendu empile les
        draw() et l'affichage met un temps notable à rattraper la position
        réelle. Ici : premier événement d'une rafale -> rendu immédiat ;
        événements suivants pendant la fenêtre de throttle -> seul l'état
        est mis à jour, un seul rendu de rattrapage est garanti à la fin.
        """
        if not self._redraw_timer.isActive():
            self.canvas.draw_idle()
            self._redraw_pending = False
            self._redraw_timer.start()
        else:
            self._redraw_pending = True

    def _on_redraw_timeout(self):
        if self._redraw_pending:
            self.canvas.draw_idle()
            self._redraw_pending = False

    def reset_zoom(self):
        if self._full_xlim is None:
            return
        self.ax_fuel.set_xlim(*self._full_xlim)
        self._rescale_y()
        self._update_zoom_button_state()
        self._request_redraw()

    def _rescale_y(self):
        if self._fuel is None:
            return
        x_min, x_max = self.ax_fuel.get_xlim()
        ylim = _rescaled_ylim(self._fuel, x_min, x_max)
        if ylim is not None:
            self.ax_fuel.set_ylim(*ylim)

    def _update_zoom_button_state(self):
        if self._full_xlim is None:
            return
        x_min, x_max = self.ax_fuel.get_xlim()
        full_min, full_max = self._full_xlim
        is_zoomed = (x_min > full_min + 0.5) or (x_max < full_max - 0.5)
        set_button_enabled(self.reset_btn, is_zoomed)

    def _on_scroll(self, event):
        if self._full_xlim is None or event.inaxes not in (self.ax_fuel, self.ax_status):
            return
        factor = (1 / ZOOM_SCALE) if event.button == "up" else ZOOM_SCALE
        x_min, x_max = self.ax_fuel.get_xlim()
        new_xlim = _zoomed_xlim(x_min, x_max, event.xdata, factor, self._full_xlim)
        self.ax_fuel.set_xlim(*new_xlim)
        self._rescale_y()
        self._update_zoom_button_state()
        self._request_redraw()

    def _on_button_press(self, event):
        if self._full_xlim is None or event.inaxes not in (self.ax_fuel, self.ax_status):
            return
        if event.dblclick:
            self.reset_zoom()
            return
        if event.button != 1 or event.x is None:
            return
        self._pan_start = {"x_pixel": event.x, "xlim": self.ax_fuel.get_xlim()}

    def _on_motion(self, event):
        if self._pan_start is None or event.x is None:
            return
        bbox = self.ax_fuel.get_window_extent()
        if bbox.width == 0:
            return
        x_min0, x_max0 = self._pan_start["xlim"]
        data_per_pixel = (x_max0 - x_min0) / bbox.width
        dx = (self._pan_start["x_pixel"] - event.x) * data_per_pixel
        new_xlim = _panned_xlim((x_min0, x_max0), dx, self._full_xlim)
        self.ax_fuel.set_xlim(*new_xlim)
        self._rescale_y()
        self._request_redraw()

    def _on_button_release(self, event):
        self._pan_start = None
        self._update_zoom_button_state()
        if self._redraw_pending:
            # rendu final immediat au relachement, sans attendre le timer
            self._redraw_timer.stop()
            self._redraw_pending = False
            self.canvas.draw_idle()