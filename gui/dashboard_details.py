"""
Détail des vols derrière chaque élément du Dashboard : textes d'infobulle
(résumé par site) et fenêtre de détail (liste triable des sites ou des vols).
La logique d'agrégation est sans Qt pour pouvoir être testée seule.
"""

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHeaderView, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QHBoxLayout,
)

from gui.cursor_utils import apply_pointer_cursor

TOOLTIP_MAX_SITES = 8


# ----------------------------------------------------------------- agrégation

def summarize_by_site(events):
    """
    events : [(datetime, heure, litres, site), ...]
    -> [(site, nb_vols, litres), ...] trié par litres décroissants.
    """
    totals = defaultdict(lambda: [0, 0.0])
    for _ts, _hour, loss, site in events:
        totals[site][0] += 1
        totals[site][1] += loss
    return sorted(((s, c, l) for s, (c, l) in totals.items()), key=lambda r: (-r[2], r[0]))


def tooltip_text(title, events):
    """Texte d'infobulle : un titre, puis les sites concernés (les plus touchés d'abord)."""
    if not events:
        return f"{title}\nAucun vol"
    rows = summarize_by_site(events)
    total_loss = sum(r[2] for r in rows)
    plural = "s" if len(events) > 1 else ""
    lines = [f"{title} — {len(events)} vol{plural} · {total_loss:.0f} L"]
    for site, count, loss in rows[:TOOLTIP_MAX_SITES]:
        lines.append(f"  • {site} : {count} vol{'s' if count > 1 else ''} · {loss:.0f} L")
    if len(rows) > TOOLTIP_MAX_SITES:
        lines.append(f"  … et {len(rows) - TOOLTIP_MAX_SITES} autre(s) site(s)")
    lines.append("Cliquer pour le détail")
    return "\n".join(lines)


# ------------------------------------------------------------ fenêtre de détail

class _SortItem(QTableWidgetItem):
    """Cellule affichant un texte mais triée sur une clé (nombre, date ISO...)."""

    def __init__(self, text, key=None, align_center=False):
        super().__init__(text)
        self.key = text if key is None else key
        if align_center:
            self.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def __lt__(self, other):
        if isinstance(other, _SortItem):
            try:
                return self.key < other.key
            except TypeError:
                return str(self.key) < str(other.key)
        return super().__lt__(other)


class DetailDialog(QDialog):
    """Fenêtre non modale réutilisée : elle reste ouverte et se met à jour à chaque clic."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Détail")
        self.resize(640, 460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("mutedLabel")
        self.subtitle.setWordWrap(True)
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        close_row = QHBoxLayout()
        close_row.addStretch(1)
        close_button = QPushButton("Fermer")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.close)
        apply_pointer_cursor(close_button)
        close_row.addWidget(close_button)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(close_row)

    def _fill(self, title, subtitle, headers, rows, stretch_column=0):
        self.title.setText(title)
        self.subtitle.setText(subtitle)
        self.table.setSortingEnabled(False)  # pas de tri pendant le remplissage
        self.table.clear()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, item in enumerate(row):
                self.table.setItem(r, c, item)
        header = self.table.horizontalHeader()
        for c in range(len(headers)):
            header.setSectionResizeMode(
                c, QHeaderView.ResizeMode.Stretch if c == stretch_column
                else QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.setSortingEnabled(True)
        self.show()
        self.raise_()
        self.activateWindow()

    def show_events(self, title, events, subtitle=""):
        """Liste des vols : site, date et heure, litres (les plus récents d'abord)."""
        rows = [
            (
                _SortItem(site),
                _SortItem(f"{ts:%d/%m/%Y %H:%M}", ts),
                _SortItem(f"{loss:.1f} L", loss, align_center=True),
            )
            for ts, _hour, loss, site in sorted(events, key=lambda e: e[0], reverse=True)
        ]
        sites = len({e[3] for e in events})
        total = sum(e[2] for e in events)
        summary = f"{len(events)} vol(s) · {sites} site(s) · {total:.1f} L au total"
        self._fill(title, f"{subtitle}\n{summary}".strip(), ["Site", "Date et heure", "Fuel perdu"], rows)

    def show_sites(self, title, site_rows, subtitle=""):
        """site_rows : [(site, nb_vols, litres, dernière_extraction), ...]"""
        rows = [
            (
                _SortItem(site),
                _SortItem(str(count), int(count), align_center=True),
                _SortItem(f"{float(loss or 0):.1f} L", float(loss or 0), align_center=True),
                _SortItem(str(last_seen or "").replace("T", " ")[:16]),
            )
            for site, count, loss, last_seen in site_rows
        ]
        total_count = sum(int(r[1]) for r in site_rows)
        total_loss = sum(float(r[2] or 0) for r in site_rows)
        summary = f"{len(site_rows)} site(s) · {total_count} période(s) de vol · {total_loss:.1f} L"
        self._fill(title, f"{subtitle}\n{summary}".strip(),
                   ["Site", "Périodes de vol", "Fuel volé", "Dernière extraction"], rows)
