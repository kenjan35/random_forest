"""Helpers communs aux graphiques du dashboard."""

FONT_SIZE = 9


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
