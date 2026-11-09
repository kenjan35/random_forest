"""Helpers du graphique quotidien du dashboard."""

from datetime import date, timedelta

import numpy as np
from matplotlib.dates import AutoDateLocator, DateFormatter, date2num
from matplotlib.ticker import MaxNLocator

from gui.dashboard_charts_utils import FONT_SIZE, empty_message, style_axes


def daily_series(rows):
    parsed = {}
    for day, count, loss in rows:
        try:
            parsed[date.fromisoformat(str(day)[:10])] = (int(count), float(loss or 0))
        except ValueError:
            continue
    if not parsed:
        return [], [], []
    first, last = min(parsed), max(parsed)
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    counts = [parsed.get(d, (0, 0.0))[0] for d in days]
    losses = [parsed.get(d, (0, 0.0))[1] for d in days]
    return days, counts, losses


def plot_daily(figure, ax, days, counts, losses, t):
    x = date2num(days)
    ax.bar(x, counts, width=0.8, color=t["mark"], edgecolor=t["edge"], linewidth=1, zorder=2)
    style_axes(figure, [ax], t)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
    ax.xaxis.set_major_locator(AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m"))
    ax.set_xlim(x[0] - 0.7, x[-1] + 0.7)
    ax.set_ylim(0, max(counts) * 1.25 + 0.5)
    peak = int(np.argmax(counts))
    ax.annotate(f"{counts[peak]} vols · {losses[peak]:.0f} L", (x[peak], counts[peak]),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=FONT_SIZE, color=t["text"])


def draw_daily(figure, ax, rows, t):
    """Barres : nombre de vols détectés par jour."""
    ax.clear()
    days, counts, losses = daily_series(rows)
    if not days:
        empty_message(ax, t, "Aucun vol enregistré pour l'instant")
        figure.patch.set_facecolor(t["surface"])
        return [], [], []
    plot_daily(figure, ax, days, counts, losses, t)
    return days, counts, losses
