"""
Dessin des graphiques du Dashboard, séparé du widget Qt pour pouvoir être
testé (et prévisualisé) sans interface. Chaque fonction reçoit des axes
matplotlib déjà créés, les données brutes de site_history et un thème.
"""

from collections import Counter
from datetime import date, datetime, timedelta

import numpy as np
from matplotlib.dates import AutoDateLocator, DateFormatter, date2num
from matplotlib.ticker import FuncFormatter, MaxNLocator

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


def style_axes(figure, axes, t, grid_axis="y"):
    """Fond, textes et grille discrets, communs à tous les graphiques."""
    figure.patch.set_facecolor(t["surface"])
    for ax in axes:
        ax.set_facecolor(t["surface"])
        ax.tick_params(colors=t["muted"], labelsize=FONT_SIZE, length=0)
        ax.xaxis.label.set_color(t["muted"])
        ax.yaxis.label.set_color(t["muted"])
        for side, spine in ax.spines.items():
            spine.set_visible(side == "bottom")
            spine.set_color(t["grid"])
        if grid_axis:
            ax.grid(axis=grid_axis, color=t["grid"], linewidth=0.8)
        ax.set_axisbelow(True)


def empty_message(ax, t, message):
    ax.clear()
    ax.set_facecolor(t["surface"])
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.text(0.5, 0.5, message, ha="center", va="center", color=t["muted"],
            fontsize=FONT_SIZE + 1, transform=ax.transAxes)


# ---------------------------------------------------------------------------
# Vols par jour
# ---------------------------------------------------------------------------

def daily_series(rows):
    """
    rows : [(jour 'YYYY-MM-DD', nb_vols, litres), ...] (site_history).
    Retourne une série CONTINUE : les jours sans vol valent 0 au lieu d'être
    absents (sinon une ligne relie deux jours éloignés et ment sur la tendance).
    """
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


def draw_daily(figure, ax, rows, t):
    """Barres : nombre de vols détectés par jour."""
    ax.clear()
    days, counts, losses = daily_series(rows)
    if not days:
        empty_message(ax, t, "Aucun vol enregistré pour l'instant")
        figure.patch.set_facecolor(t["surface"])
        return [], [], []

    x = date2num(days)
    ax.bar(x, counts, width=0.8, color=t["mark"], edgecolor=t["edge"], linewidth=1, zorder=2)
    style_axes(figure, [ax], t)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=4))
    ax.xaxis.set_major_locator(AutoDateLocator(minticks=4, maxticks=10))
    ax.xaxis.set_major_formatter(DateFormatter("%d/%m"))
    ax.set_xlim(x[0] - 0.7, x[-1] + 0.7)
    ax.set_ylim(0, max(counts) * 1.25 + 0.5)

    # libellé direct sur le seul jour le plus touché (pas un chiffre par barre)
    peak = int(np.argmax(counts))
    ax.annotate(f"{counts[peak]} vols · {losses[peak]:.0f} L", (x[peak], counts[peak]),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=FONT_SIZE, color=t["text"])
    return days, counts, losses


# ---------------------------------------------------------------------------
# Heures des vols
# ---------------------------------------------------------------------------

def hour_counts(points):
    """Nombre de vols par heure de la journée (0..23)."""
    counter = Counter(int(hour) for _ts, hour, _loss in points)
    return np.array([counter.get(h, 0) for h in range(24)])


def marker_sizes(losses):
    """Taille du point ~ litres volés (aire proportionnelle, bornée)."""
    losses = np.asarray(losses, dtype=float)
    return np.clip(20 + losses * 0.6, 20, 160)


def draw_hours(figure, ax_scatter, ax_hist, points, start_date, end_date, t):
    """
    Gauche : chaque vol placé à sa date (x) et à son heure (y) ; la taille du
    point suit les litres volés. Droite : total des vols par heure, axe des
    heures partagé, heure de pointe mise en avant et étiquetée.
    Retourne l'objet scatter (pour le survol) ou None.
    """
    ax_scatter.clear()
    ax_hist.clear()
    if not points:
        empty_message(ax_scatter, t, "Aucun vol sur la période choisie")
        empty_message(ax_hist, t, "")
        figure.patch.set_facecolor(t["surface"])
        return None

    stamps, hours, losses = zip(*points)
    x = date2num(stamps)
    # position verticale = heure + minutes, pour ne pas empiler les points
    y = [ts.hour + ts.minute / 60 for ts in stamps]
    scatter = ax_scatter.scatter(
        x, y, s=marker_sizes(losses), color=t["mark"], alpha=0.75,
        edgecolors=t["edge"], linewidths=1, zorder=3,
    )
    style_axes(figure, [ax_scatter, ax_hist], t, grid_axis=None)
    ax_scatter.grid(axis="y", color=t["grid"], linewidth=0.8)

    hour_formatter = FuncFormatter(lambda v, _pos: f"{int(v) % 24:02d}h")
    ax_scatter.set_ylim(24.6, -0.6)  # minuit en haut (lecture d'agenda), marge pour ne pas couper les points
    ax_scatter.set_yticks(range(0, 25, 3))
    ax_scatter.yaxis.set_major_formatter(hour_formatter)

    x_min = date2num(datetime.combine(start_date, datetime.min.time()))
    x_max = date2num(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    pad = (x_max - x_min) * 0.015
    ax_scatter.set_xlim(x_min - pad, x_max + pad)
    span_days = (end_date - start_date).days + 1
    ax_scatter.xaxis.set_major_locator(AutoDateLocator(minticks=3, maxticks=8))
    ax_scatter.xaxis.set_major_formatter(DateFormatter("%d/%m %Hh" if span_days <= 2 else "%d/%m"))

    counts = hour_counts(points)
    peak = int(np.argmax(counts))
    colors = [t["mark"] if h == peak else t["mark_soft"] for h in range(24)]
    ax_hist.barh(np.arange(24) + 0.5, counts, height=0.8, color=colors,
                 edgecolor=t["edge"], linewidth=1, zorder=2)
    ax_hist.grid(axis="x", color=t["grid"], linewidth=0.8)
    ax_hist.tick_params(labelleft=False)
    ax_hist.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    ax_hist.set_xlim(0, counts.max() * 1.6 + 0.5)
    ax_hist.annotate(f"{peak:02d}h : {counts[peak]}", (counts[peak], peak + 0.5),
                     xytext=(4, 0), textcoords="offset points", va="center",
                     fontsize=FONT_SIZE, color=t["text"])
    ax_hist.set_title("Vols par heure", fontsize=FONT_SIZE, color=t["muted"], loc="left")
    return scatter
