import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QSplitter, QAbstractItemView,
    QListWidget, QListWidgetItem, QMessageBox
)

from gui.chart import FuelChart
from gui.workers import BatchScanWorker
from gui.export import tagged_events, event_list_label, write_events_csv
from gui.cursor_utils import apply_pointer_cursor, set_button_enabled, set_button_busy

COL_FILE, COL_STATUS, COL_EVENTS, COL_FIRST_ALERT = range(4)

# alias conservé pour compatibilité
build_tagged_events = tagged_events


class NumericItem(QTableWidgetItem):
    """Item de tableau qui se trie numériquement plutôt qu'alphabétiquement."""

    def __init__(self, value):
        super().__init__(str(value))
        self.value = value

    def __lt__(self, other):
        if isinstance(other, NumericItem):
            return self.value < other.value
        return super().__lt__(other)


class BatchScanTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        row = QHBoxLayout()
        self.choose_btn = QPushButton("Choisir un dossier…")
        self.choose_btn.clicked.connect(self.choose_folder)
        apply_pointer_cursor(self.choose_btn)
        self.select_all_btn = QPushButton("Tout sélectionner")
        self.select_all_btn.setObjectName("secondary")
        self.select_all_btn.setEnabled(False)
        self.select_all_btn.clicked.connect(self.select_all_rows)
        apply_pointer_cursor(self.select_all_btn)
        self.export_btn = QPushButton("Exporter en CSV")
        self.export_btn.setObjectName("secondary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)
        apply_pointer_cursor(self.export_btn)
        self.folder_label = QLabel("Aucun dossier sélectionné")
        self.folder_label.setObjectName("pathLabel")
        row.addWidget(self.choose_btn)
        row.addWidget(self.select_all_btn)
        row.addWidget(self.export_btn)
        row.addWidget(self.folder_label, stretch=1)
        root.addLayout(row)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        splitter = QSplitter(Qt.Vertical)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Fichier", "Statut", "Nb périodes", "Première alerte"])
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        splitter.addWidget(self.table)

        detail_splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Période(s) suspecte(s)")
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)
        self.events_list = QListWidget()
        left_layout.addWidget(self.events_list)

        self.chart = FuelChart()

        detail_splitter.addWidget(left)
        detail_splitter.addWidget(self.chart)
        detail_splitter.setStretchFactor(0, 1)
        detail_splitter.setStretchFactor(1, 2)

        splitter.addWidget(detail_splitter)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier contenant des CSV")
        if folder:
            self.start_scan(folder)

    def start_scan(self, folder):
        self.folder_label.setText(folder)
        self.table.setSortingEnabled(False)  # évite le tri en plein remplissage (lignes/colonnes désynchronisées)
        self.table.setRowCount(0)
        set_button_enabled(self.export_btn, False)
        set_button_enabled(self.select_all_btn, False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        set_button_busy(self.choose_btn, True)
        set_button_enabled(self.choose_btn, False)

        self.worker = BatchScanWorker(folder)
        self.worker.progress.connect(self.on_progress)
        self.worker.file_done.connect(self.on_file_done)
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()

    def on_progress(self, done, total, current_file):
        self.progress.setMaximum(total)
        self.progress.setValue(done)

    def on_file_done(self, result):
        row = self.table.rowCount()
        self.table.insertRow(row)

        filename = result.get("filename") or os.path.basename(result["csv_path"])
        file_item = QTableWidgetItem(filename)
        file_item.setData(Qt.ItemDataRole.UserRole, result)  # attaché à l'item -> suit la ligne même après un tri
        self.table.setItem(row, COL_FILE, file_item)

        if result.get("error"):
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("Erreur"))
            self.table.setItem(row, COL_EVENTS, NumericItem(-1))
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(result["error"]))
        elif result["has_theft"]:
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("⚠️ Suspect"))
            self.table.setItem(row, COL_EVENTS, NumericItem(result["n_events"]))
            first_ts = result["events"][0]["ts_start"] if result["events"] else ""
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(first_ts))
        elif result.get("has_sensor_glitch"):
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("Data incomplete"))
            self.table.setItem(row, COL_EVENTS, NumericItem(result["n_events_ignored"]))
            first_ts = result["events_ignored"][0]["ts_start"] if result["events_ignored"] else ""
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(first_ts))
        else:
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("✅ Normal"))
            self.table.setItem(row, COL_EVENTS, NumericItem(0))
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(""))

    def on_finished(self):
        self.progress.setVisible(False)
        set_button_busy(self.choose_btn, False)
        set_button_enabled(self.choose_btn, True)
        has_rows = self.table.rowCount() > 0
        set_button_enabled(self.export_btn, has_rows)
        set_button_enabled(self.select_all_btn, has_rows)
        self.table.setSortingEnabled(True)  # le tri ne reprend qu'une fois toutes les lignes remplies

    def select_all_rows(self):
        self.table.selectAll()

    def on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        file_item = self.table.item(row, COL_FILE)
        result = file_item.data(Qt.ItemDataRole.UserRole) if file_item else None

        self.events_list.clear()
        if not result or result.get("error"):
            self.chart.clear()
            return

        for ev, label in tagged_events(result):
            self.events_list.addItem(QListWidgetItem(event_list_label(ev, label)))

        # le résultat stocké lors du scan contient déjà tout ce qu'il faut pour le graphique
        self.chart.plot(result)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les résultats", "resultats_scan.csv", "CSV (*.csv)")
        if not path:
            return
        results = []
        for row in range(self.table.rowCount()):
            file_item = self.table.item(row, COL_FILE)
            results.append(file_item.data(Qt.ItemDataRole.UserRole) if file_item else None)
        try:
            write_events_csv(path, results, mapping_key="filename")
        except OSError as exc:
            QMessageBox.warning(self, "Export CSV", f"Impossible d'écrire le fichier (est-il ouvert dans Excel ?)\n{exc}")
