from datetime import date, datetime

import numpy as np

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QHeaderView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QScrollArea,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.dates import DateFormatter, date2num
from matplotlib.figure import Figure

from gui.cursor_utils import apply_pointer_cursor
from gui.dashboard_charts import draw_daily, draw_hours, theme
from gui.dashboard_details import DetailDialog, tooltip_text
from gui.site_history import (
    get_dashboard_summary,
    get_recent_theft_events,
    get_theft_daily_points,
    get_theft_hour_points,
    get_top_sites,
    get_top_theft_hours,
)

DEFAULT_HOUR_RANGE_DAYS = 30   # période affichée par défaut sur le graphique des heures
HOVER_RADIUS_PX = 10
CLICK_TOLERANCE_PX = 4   # au-delà, un clic-glisser est un déplacement, pas un clic


def _parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)


class ClickableCard(QFrame):
    """Carte KPI cliquable (ouvre le détail des sites ou des vols derrière le chiffre)."""
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class TopSitesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._dark_mode = False
        self._daily = ([], [], [])          # jours, nb vols, litres
        self._hour_points = []              # [(datetime, heure, litres, site), ...]
        self._hour_scatter = None
        self._hour_full_xlim = None
        self._hour_pan_start = None
        self._all_hour_points = []          # tous les vols horodatés (datetime, heure, litres, site)
        self._peak_hour = None
        self._detail = None
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)
        root.setAlignment(Qt.AlignmentFlag.AlignTop)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel("Tableau de bord")
        title.setObjectName("pageTitle")
        titles.addWidget(title)
        subtitle = QLabel("Cumul des vols détectés pendant les extractions Power-Noc.")
        subtitle.setObjectName("mutedLabel")
        titles.addWidget(subtitle)
        header.addLayout(titles, stretch=1)
        self.status_label = QLabel()
        self.status_label.setObjectName("mutedLabel")
        refresh_button = QPushButton("Actualiser")
        refresh_button.clicked.connect(self.refresh)
        apply_pointer_cursor(refresh_button)
        header.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignBottom)
        header.addWidget(refresh_button, alignment=Qt.AlignmentFlag.AlignBottom)
        root.addLayout(header)

        metrics_layout = QHBoxLayout()
        self.metric_values = {}
        card_hints = {
            "sites": "Cliquer pour voir la liste des sites touchés",
            "events": "Cliquer pour voir tous les vols",
            "fuel": "Cliquer pour voir le fuel volé par site",
            "peak": "Cliquer pour voir les vols de cette heure",
        }
        for key, label in (("sites", "Sites touchés"), ("events", "Périodes de vol"),
                           ("fuel", "Fuel volé"), ("peak", "Heure de pointe")):
            card = ClickableCard()
            card.setObjectName("metricCard")
            card.setToolTip(card_hints[key])
            card.clicked.connect(lambda key=key: self._on_metric_clicked(key))
            card.setMinimumHeight(92)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 12, 14, 12)
            card_layout.setSpacing(2)
            value = QLabel("-")
            value.setObjectName(f"metricValue{key.capitalize()}")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(value)
            caption = QLabel(f"{label}  ›")
            caption.setObjectName("metricCaption")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(caption)
            metrics_layout.addWidget(card, stretch=1)
            self.metric_values[key] = value
        root.addLayout(metrics_layout)

        # --- classements ---
        self.table = self._make_table(
            ["Rang", "Site", "Périodes de vol", "Fuel volé total", "Dernière extraction"], stretch_column=1
        )
        self.hours_table = self._make_table(["Rang", "Fourchette horaire", "Périodes de vol"], stretch_column=2)
        self.table.cellClicked.connect(self._on_top_site_clicked)
        self.hours_table.cellClicked.connect(self._on_top_hour_clicked)
        for table in (self.table, self.hours_table):
            table.viewport().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            table.setToolTip("Cliquer sur une ligne pour voir les vols")
        tables_layout = QHBoxLayout()
        tables_layout.setSpacing(16)
        tables_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        tables_layout.addLayout(self._section("Top 5 des sites les plus volés", self.table), stretch=3)
        tables_layout.addLayout(self._section("Top 5 des heures de vol", self.hours_table), stretch=2)
        root.addLayout(tables_layout)

        # --- vols par jour ---
        root.addSpacing(8)
        daily_header = QHBoxLayout()
        daily_title = QLabel("Vols détectés par jour")
        daily_title.setObjectName("sectionTitle")
        daily_header.addWidget(daily_title)
        daily_header.addStretch(1)
        root.addLayout(daily_header)

        self.daily_figure = Figure(figsize=(8, 2.2), layout="constrained")
        self.daily_canvas = FigureCanvas(self.daily_figure)
        self.daily_canvas.setFixedHeight(220)
        self.daily_axes = self.daily_figure.add_subplot(111)
        self.daily_canvas.mpl_connect("motion_notify_event", self._on_daily_motion)
        self.daily_canvas.mpl_connect("button_release_event", self._on_daily_click)
        self.daily_canvas.mpl_connect("figure_leave_event", lambda _e: QToolTip.hideText())
        root.addWidget(self.daily_canvas)

        # --- heures des vols ---
        root.addSpacing(8)
        hour_header = QHBoxLayout()
        hour_title = QLabel("Heure de chaque vol")
        hour_title.setObjectName("sectionTitle")
        hour_header.addWidget(hour_title)
        hour_header.addSpacing(16)
        hour_header.addWidget(QLabel("Du"))
        self.hour_start_date_edit = QDateEdit()
        self.hour_end_date_edit = QDateEdit()
        for date_edit in (self.hour_start_date_edit, self.hour_end_date_edit):
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat("dd/MM/yyyy")
            date_edit.setEnabled(False)
            date_edit.dateChanged.connect(self._on_hour_date_changed)
        hour_header.addWidget(self.hour_start_date_edit)
        hour_header.addWidget(QLabel("au"))
        hour_header.addWidget(self.hour_end_date_edit)
        hour_header.addStretch(1)
        root.addLayout(hour_header)

        hint = QLabel("Taille du point = litres volés · survol : sites concernés · clic : détail · "
                      "molette : zoom · glisser : déplacer · double-clic : vue complète")
        hint.setObjectName("mutedLabel")
        root.addWidget(hint)

        self.hour_figure = Figure(figsize=(8, 2.9), layout="constrained")
        grid = self.hour_figure.add_gridspec(1, 2, width_ratios=[4, 1])
        self.hour_axes = self.hour_figure.add_subplot(grid[0])
        self.hour_hist_axes = self.hour_figure.add_subplot(grid[1], sharey=self.hour_axes)
        self.hour_canvas = FigureCanvas(self.hour_figure)
        self.hour_canvas.setFixedHeight(300)
        self.hour_canvas.mpl_connect("button_press_event", self._on_hour_button_press)
        self.hour_canvas.mpl_connect("scroll_event", self._on_hour_scroll)
        self.hour_canvas.mpl_connect("motion_notify_event", self._on_hour_motion)
        self.hour_canvas.mpl_connect("button_release_event", self._on_hour_button_release)
        self.hour_canvas.mpl_connect("figure_leave_event", lambda _e: QToolTip.hideText())
        root.addWidget(self.hour_canvas)

        # --- alertes récentes ---
        root.addSpacing(8)
        recent_title = QLabel("Alertes récentes")
        recent_title.setObjectName("sectionTitle")
        root.addWidget(recent_title)
        self.recent_table = QTableWidget(0, 3)
        self.recent_table.setHorizontalHeaderLabels(["Site", "Date et heure", "Fuel perdu"])
        self.recent_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.recent_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.recent_table.verticalHeader().setVisible(False)
        self.recent_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.recent_table.horizontalHeader().setStretchLastSection(True)
        self.recent_table.setFixedHeight(260)
        self.recent_table.cellClicked.connect(self._on_recent_clicked)
        self.recent_table.viewport().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.recent_table.setToolTip("Cliquer sur une ligne pour voir tous les vols de ce site")
        root.addWidget(self.recent_table)
        root.addStretch(1)

        scroll.setWidget(content)
        outer.addWidget(scroll)

    @staticmethod
    def _make_table(headers, stretch_column):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.verticalHeader().setVisible(False)
        for column in range(len(headers)):
            mode = (QHeaderView.ResizeMode.Stretch if column == stretch_column
                    else QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(column, mode)
        return table

    @staticmethod
    def _section(title_text, widget):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        title = QLabel(title_text)
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignTop)
        return layout

    # ------------------------------------------------------------- données

    def refresh(self):
        sites_count, event_count, fuel_loss = get_dashboard_summary()
        self.metric_values["sites"].setText(str(sites_count))
        self.metric_values["events"].setText(str(event_count))
        self.metric_values["fuel"].setText(f"{float(fuel_loss or 0):,.0f} L".replace(",", " "))

        rows = get_top_sites()
        self.table.setRowCount(len(rows))
        for rank, (site, theft_count, site_loss, _extractions, last_seen) in enumerate(rows, start=1):
            values = (str(rank), site, str(theft_count), f"{float(site_loss or 0):.1f} L",
                      str(last_seen).replace("T", " ")[:16])
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(rank - 1, column, item)
        self.status_label.setText(
            f"{len(rows)} site(s) classé(s)" if rows else "Aucune période de vol enregistrée"
        )

        hour_rows = get_top_theft_hours()
        self._peak_hour = int(hour_rows[0][0]) if hour_rows else None
        self.metric_values["peak"].setText(f"{self._peak_hour:02d}h" if hour_rows else "-")
        self.hours_table.setRowCount(len(hour_rows))
        for rank, (hour_bucket, theft_count, _total) in enumerate(hour_rows, start=1):
            hour = int(hour_bucket)
            values = (str(rank), f"{hour:02d}:00 - {hour:02d}:59", str(theft_count))
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.hours_table.setItem(rank - 1, column, item)
        self._fit_table_height(self.table)
        self._fit_table_height(self.hours_table)

        self._load_hour_points()
        self._refresh_daily_chart()
        self._refresh_recent_alerts()
        self._refresh_hour_scatter()

    def _load_hour_points(self):
        points = []
        for timestamp, hour_bucket, fuel, site in get_theft_hour_points():
            parsed = _parse_timestamp(timestamp)
            if parsed is not None:
                points.append((parsed, int(hour_bucket), float(fuel or 0), str(site)))
        self._all_hour_points = points

        edits = (self.hour_start_date_edit, self.hour_end_date_edit)
        for edit in edits:
            edit.blockSignals(True)
        if points:
            first_day, last_day = points[0][0].date(), points[-1][0].date()
            first = QDate(first_day.year, first_day.month, first_day.day)
            last = QDate(last_day.year, last_day.month, last_day.day)
            for edit in edits:
                edit.setMinimumDate(first)
                edit.setMaximumDate(last)
                edit.setEnabled(True)
            # défaut : les DEFAULT_HOUR_RANGE_DAYS derniers jours (et non le seul dernier jour)
            if not getattr(self, "_hour_range_chosen", False):
                default_start = max(first, last.addDays(-(DEFAULT_HOUR_RANGE_DAYS - 1)))
                self.hour_start_date_edit.setDate(default_start)
                self.hour_end_date_edit.setDate(last)
        else:
            for edit in edits:
                edit.setEnabled(False)
        for edit in edits:
            edit.blockSignals(False)

    # ------------------------------------------------------------ graphiques

    def _refresh_daily_chart(self):
        self._daily = draw_daily(
            self.daily_figure, self.daily_axes, get_theft_daily_points(), theme(self._dark_mode)
        )
        self.daily_canvas.draw_idle()

    def _refresh_recent_alerts(self):
        rows = get_recent_theft_events()
        self.recent_table.setRowCount(len(rows))
        for row_index, (site, timestamp, loss) in enumerate(rows):
            values = (site, str(timestamp).replace("T", " ")[:16], f"{float(loss or 0):.1f} L")
            for column, value in enumerate(values):
                self.recent_table.setItem(row_index, column, QTableWidgetItem(value))

    def _refresh_hour_scatter(self):
        start = self.hour_start_date_edit.date().toPython()
        end = self.hour_end_date_edit.date().toPython()
        all_points = getattr(self, "_all_hour_points", [])
        if not all_points:
            start = end = date.today()
        self._hour_points = [p for p in all_points if start <= p[0].date() <= end]
        self._hour_scatter = draw_hours(
            self.hour_figure, self.hour_axes, self.hour_hist_axes,
            [p[:3] for p in self._hour_points], start, end, theme(self._dark_mode),
        )
        self._hour_full_xlim = self.hour_axes.get_xlim() if self._hour_scatter is not None else None
        self.hour_canvas.draw_idle()

    def set_theme(self, is_dark):
        self._dark_mode = is_dark
        self._refresh_daily_chart()
        self._refresh_hour_scatter()

    # ------------------------------------------------- détail (fenêtre)

    def _detail_dialog(self):
        if self._detail is None:
            self._detail = DetailDialog(self)
        return self._detail

    def _events_where(self, predicate):
        return [e for e in self._all_hour_points if predicate(e)]

    def _on_metric_clicked(self, key):
        dialog = self._detail_dialog()
        if key in ("sites", "fuel"):
            rows = [(site, count, loss, last_seen)
                    for site, count, loss, _n, last_seen in get_top_sites(limit=100000)]
            if key == "fuel":
                rows.sort(key=lambda r: -float(r[2] or 0))
                dialog.show_sites("Fuel volé par site", rows, "Trié du site le plus touché au moins touché.")
            else:
                dialog.show_sites("Sites touchés", rows, "Sites ayant au moins une période de vol.")
        elif key == "events":
            dialog.show_events("Toutes les périodes de vol", self._all_hour_points)
        elif key == "peak" and self._peak_hour is not None:
            hour = self._peak_hour
            dialog.show_events(f"Vols entre {hour:02d}h00 et {hour:02d}h59",
                               self._events_where(lambda e: e[1] == hour),
                               "Heure de la journée où le plus de vols ont été détectés.")

    def _on_top_site_clicked(self, row, _column):
        item = self.table.item(row, 1)
        if item is not None:
            self._show_site(item.text())

    def _on_recent_clicked(self, row, _column):
        item = self.recent_table.item(row, 0)
        if item is not None:
            self._show_site(item.text())

    def _show_site(self, site):
        self._detail_dialog().show_events(f"Vols du site {site}", self._events_where(lambda e: e[3] == site))

    def _on_top_hour_clicked(self, row, _column):
        item = self.hours_table.item(row, 1)
        if item is not None:
            hour = int(item.text()[:2])
            self._detail_dialog().show_events(f"Vols entre {hour:02d}h00 et {hour:02d}h59",
                                              self._events_where(lambda e: e[1] == hour))

    # ------------------------------------------------- survol des graphiques

    @staticmethod
    def _show_tooltip(canvas, text):
        if text:
            QToolTip.showText(QCursor.pos(), text, canvas)
            canvas.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            QToolTip.hideText()
            canvas.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def _daily_index(self, event):
        """Jour sous le curseur (index), uniquement sur une barre non vide."""
        days, counts, _losses = self._daily
        if not days or event.inaxes is not self.daily_axes or event.xdata is None:
            return None
        index = int(round(event.xdata - date2num(days[0])))
        if 0 <= index < len(days) and counts[index] > 0 and event.ydata <= counts[index] + 0.3:
            return index
        return None

    def _events_of_day(self, day):
        return self._events_where(lambda e: e[0].date() == day)

    def _on_daily_motion(self, event):
        index = self._daily_index(event)
        if index is None:
            self._show_tooltip(self.daily_canvas, "")
            return
        day = self._daily[0][index]
        self._show_tooltip(self.daily_canvas, tooltip_text(f"{day:%d/%m/%Y}", self._events_of_day(day)))

    def _on_daily_click(self, event):
        if event.button != 1:
            return
        index = self._daily_index(event)
        if index is not None:
            day = self._daily[0][index]
            self._detail_dialog().show_events(f"Vols du {day:%d/%m/%Y}", self._events_of_day(day))

    def _hour_bar_at_cursor(self, event):
        """Heure (0-23) de la barre de l'histogramme sous le curseur."""
        if event.inaxes is not self.hour_hist_axes or event.ydata is None or event.xdata is None:
            return None
        hour = int(event.ydata)
        if not 0 <= hour <= 23:
            return None
        count = sum(1 for p in self._hour_points if p[0].hour == hour)
        return hour if count and event.xdata <= count + 0.5 else None

    def _hour_points_at_cursor(self, event):
        """Tous les vols sous le curseur (plusieurs points peuvent se superposer)."""
        if (self._hour_scatter is None or event.inaxes is not self.hour_axes
                or event.x is None or not self._hour_points):
            return []
        pixels = self.hour_axes.transData.transform(self._hour_scatter.get_offsets())
        sizes = self._hour_scatter.get_sizes()
        distances = np.hypot(pixels[:, 0] - event.x, pixels[:, 1] - event.y)
        radius = np.maximum(HOVER_RADIUS_PX, np.sqrt(sizes) * 0.75)
        return [self._hour_points[i] for i in np.flatnonzero(distances <= radius)]

    def _hour_hover(self, event):
        """(titre, vols) de l'élément sous le curseur, ou (None, [])."""
        points = self._hour_points_at_cursor(event)
        if points:
            if len(points) == 1:
                ts, _h, loss, site = points[0]
                return f"{site}\n{ts:%d/%m/%Y %H:%M} · {loss:.1f} L\nCliquer pour tous les vols de ce site", points
            return f"{len(points)} vols superposés", points
        hour = self._hour_bar_at_cursor(event)
        if hour is not None:
            return f"Entre {hour:02d}h00 et {hour:02d}h59", [p for p in self._hour_points if p[0].hour == hour]
        return None, []

    def _on_hour_motion(self, event):
        if self._hour_pan_start is not None:
            self._pan_hours(event)
            return
        title, points = self._hour_hover(event)
        if title is None:
            self._show_tooltip(self.hour_canvas, "")
        elif len(points) == 1:
            self._show_tooltip(self.hour_canvas, title)
        else:
            self._show_tooltip(self.hour_canvas, tooltip_text(title, points))

    def _on_hour_click(self, event):
        title, points = self._hour_hover(event)
        if title is None:
            return
        period = (f"Période affichée : {self.hour_start_date_edit.date().toString('dd/MM/yyyy')}"
                  f" au {self.hour_end_date_edit.date().toString('dd/MM/yyyy')}")
        if len(points) == 1:
            self._show_site(points[0][3])
        else:
            self._detail_dialog().show_events(title.split("\n")[0], points, period)

    def _on_hour_date_changed(self):
        self._hour_range_chosen = True
        start, end = self.hour_start_date_edit.date(), self.hour_end_date_edit.date()
        if start > end:
            if self.sender() is self.hour_start_date_edit:
                self.hour_end_date_edit.setDate(start)
            else:
                self.hour_start_date_edit.setDate(end)
            return  # le setDate ci-dessus relance ce gestionnaire
        self._refresh_hour_scatter()

    # ------------------------------------------- zoom / déplacement (dates)
    # Les heures (axe vertical) restent fixes 0h-24h : seul l'axe des dates bouge.

    def _clamp_x(self, x_min, x_max):
        full_min, full_max = self._hour_full_xlim
        width = min(x_max - x_min, full_max - full_min)
        x_min = max(full_min, min(x_min, full_max - width))
        return x_min, x_min + width

    def _on_hour_scroll(self, event):
        if self._hour_full_xlim is None or event.inaxes is not self.hour_axes or event.xdata is None:
            return
        factor = 0.8 if event.button == "up" else 1.25
        x_min, x_max = self.hour_axes.get_xlim()
        ratio = (event.xdata - x_min) / (x_max - x_min)
        width = (x_max - x_min) * factor
        min_width = 1 / 24 * 6  # pas plus fin que 6 heures
        width = max(width, min_width)
        new_min = event.xdata - ratio * width
        self.hour_axes.set_xlim(*self._clamp_x(new_min, new_min + width))
        self._update_date_format()
        self.hour_canvas.draw_idle()

    def _on_hour_button_press(self, event):
        if event.button == 1 and event.inaxes is self.hour_hist_axes:
            self._hour_press_x = event.x  # clic sur l'histogramme : pas de déplacement
            return
        if self._hour_full_xlim is None or event.inaxes is not self.hour_axes:
            return
        if event.dblclick:
            self.hour_axes.set_xlim(*self._hour_full_xlim)
            self._update_date_format()
            self.hour_canvas.draw_idle()
            return
        if event.button == 1 and event.x is not None:
            self._hour_pan_start = (event.x, self.hour_axes.get_xlim())
            self._hour_press_x = event.x
            QToolTip.hideText()

    def _pan_hours(self, event):
        if event.x is None:
            return
        start_x, (x_min, x_max) = self._hour_pan_start
        width_px = self.hour_axes.get_window_extent().width or 1
        shift = (start_x - event.x) * (x_max - x_min) / width_px
        self.hour_axes.set_xlim(*self._clamp_x(x_min + shift, x_max + shift))
        self.hour_canvas.draw_idle()

    def _on_hour_button_release(self, event):
        self._hour_pan_start = None
        press_x = getattr(self, "_hour_press_x", None)
        self._hour_press_x = None
        # un clic sans déplacement ouvre le détail de l'élément cliqué
        if (event.button == 1 and press_x is not None and event.x is not None
                and abs(event.x - press_x) <= CLICK_TOLERANCE_PX):
            self._on_hour_click(event)

    def _update_date_format(self):
        """Affiche aussi l'heure sur l'axe quand on a zoomé sur moins de 2 jours."""
        x_min, x_max = self.hour_axes.get_xlim()
        fmt = "%d/%m %Hh" if (x_max - x_min) <= 2 else "%d/%m"
        self.hour_axes.xaxis.set_major_formatter(DateFormatter(fmt))

    @staticmethod
    def _fit_table_height(table):
        visible_rows = min(max(table.rowCount(), 1), 5)
        height = (
            table.horizontalHeader().height()
            + visible_rows * table.verticalHeader().defaultSectionSize()
            + 2 * table.frameWidth()
        )
        table.setFixedHeight(height)
