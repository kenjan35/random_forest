"""Helpers du graphique horaire du dashboard."""

from collections import Counter
from datetime import datetime, timedelta

import numpy as np
from matplotlib.dates import AutoDateLocator, DateFormatter, date2num
from matplotlib.ticker import FuncFormatter, MaxNLocator

from gui.dashboard_charts_utils import FONT_SIZE, empty_message, style_axes


def hour_counts(points):
    counter = Counter(int(hour) for _ts, hour, _loss in points)
    return np.array([counter.get(h, 0) for h in range(24)])


def marker_sizes(losses):
    losses = np.asarray(losses, dtype=float)
    return np.clip(20 + losses * 0.6, 20, 160)


def style_hour_axes(figure, ax_scatter, ax_hist, t, start_date, end_date):
    style_axes(figure, [ax_scatter, ax_hist], t, grid_axis=None)
    ax_scatter.grid(axis="y", color=t["grid"], linewidth=0.8)
    hour_formatter = FuncFormatter(lambda v, _pos: f"{int(v) % 24:02d}h")
    ax_scatter.set_ylim(24.6, -0.6)
    ax_scatter.set_yticks(range(0, 25, 3))
    ax_scatter.yaxis.set_major_formatter(hour_formatter)
    x_min = date2num(datetime.combine(start_date, datetime.min.time()))
    x_max = date2num(datetime.combine(end_date + timedelta(days=1), datetime.min.time()))
    pad = (x_max - x_min) * 0.015
    ax_scatter.set_xlim(x_min - pad, x_max + pad)
    span_days = (end_date - start_date).days + 1
    ax_scatter.xaxis.set_major_locator(AutoDateLocator(minticks=3, maxticks=8))
    ax_scatter.xaxis.set_major_formatter(DateFormatter("%d/%m %Hh" if span_days <= 2 else "%d/%m"))


def draw_hour_histogram(ax_hist, counts, peak, t):
    bar_colors = [t["mark"] if h == peak else t["mark_soft"] for h in range(24)]
    ax_hist.barh(np.arange(24) + 0.5, counts, height=0.8, color=bar_colors,
                 edgecolor=t["edge"], linewidth=1, zorder=2)
    ax_hist.grid(axis="x", color=t["grid"], linewidth=0.8)
    ax_hist.tick_params(labelleft=False)
    ax_hist.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=3))
    ax_hist.set_xlim(0, counts.max() * 1.6 + 0.5)
    ax_hist.annotate(f"{peak:02d}h : {counts[peak]}", (counts[peak], peak + 0.5),
                     xytext=(4, 0), textcoords="offset points", va="center",
                     fontsize=FONT_SIZE, color=t["text"])
    ax_hist.set_title("Vols par heure", fontsize=FONT_SIZE, color=t["muted"], loc="left")


def draw_hours(figure, ax_scatter, ax_hist, points, start_date, end_date, t):
    ax_scatter.clear()
    ax_hist.clear()
    if not points:
        empty_message(ax_scatter, t, "Aucun vol sur la période choisie")
        empty_message(ax_hist, t, "")
        figure.patch.set_facecolor(t["surface"])
        return None
    stamps, hours, losses = zip(*points)
    x = date2num(stamps)
    y = [ts.hour + ts.minute / 60 for ts in stamps]
    scatter = ax_scatter.scatter(
        x, y, s=marker_sizes(losses), color=t["mark"], alpha=0.75,
        edgecolors=t["edge"], linewidths=1, zorder=3,
    )
    style_hour_axes(figure, ax_scatter, ax_hist, t, start_date, end_date)
    counts = hour_counts(points)
    peak = int(np.argmax(counts))
    draw_hour_histogram(ax_hist, counts, peak, t)
    return scatter
