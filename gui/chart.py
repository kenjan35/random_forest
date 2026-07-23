"""
Graphique du niveau de carburant, avec les périodes suspectes surlignées
et un bandeau d'état du générateur (Actif/Inactif) en dessous.
"""

import os

import numpy as np

import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

FUEL_COLOR = "#2563eb"
ALERT_COLOR = "#ef4444"
ACTIVE_COLOR = "#22c55e"
INACTIVE_COLOR = "#cbd5e1"


class FuelChart(FigureCanvas):
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4), dpi=100, tight_layout=True)
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax_fuel = None
        self.ax_status = None
        self._build_axes()

    def _build_axes(self):
        self.fig.clear()
        gs = self.fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.08)
        self.ax_fuel = self.fig.add_subplot(gs[0])
        self.ax_status = self.fig.add_subplot(gs[1], sharex=self.ax_fuel)

    def clear(self):
        self._build_axes()
        self.draw()

    def plot(self, result):
        self._build_axes()
        fuel = result["fuel"]
        active = result["active"]
        x = np.arange(len(fuel))

        self.ax_fuel.plot(x, fuel, color=FUEL_COLOR, linewidth=1.2, label="Carburant (L)")
        for ev in result["events"]:
            self.ax_fuel.axvspan(ev["row_start"], ev["row_end"], color=ALERT_COLOR, alpha=0.25)

        title = result["filename"]
        if result["has_theft"]:
            title += f"  —  {result['n_events']} période(s) suspecte(s)"
        else:
            title += "  —  aucun vol détecté"
        self.ax_fuel.set_title(title, fontsize=11, fontweight="bold")
        self.ax_fuel.set_ylabel("Litres")
        self.ax_fuel.tick_params(labelbottom=False)
        self.ax_fuel.grid(alpha=0.2)

        # bandeau d'état du générateur, simplifié si trop de bascules pour rester lisible
        self.ax_status.fill_between(
            x, 0, 1, where=active, color=ACTIVE_COLOR, step="mid", alpha=0.6, label="Actif"
        )
        self.ax_status.fill_between(
            x, 0, 1, where=~active, color=INACTIVE_COLOR, step="mid", alpha=0.6, label="Inactif"
        )
        self.ax_status.set_yticks([])
        self.ax_status.set_xlabel("Relevé (index)")

        self.draw()
