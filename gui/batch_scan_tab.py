import csv
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QProgressBar, QSplitter, QAbstractItemView
)

from gui.chart import FuelChart
from gui.workers import BatchScanWorker
from gui.analysis import analyze_file, AnalysisError

COL_FILE, COL_STATUS, COL_EVENTS, COL_FIRST_ALERT = range(4)


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
        self.results_by_row = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        row = QHBoxLayout()
        self.choose_btn = QPushButton("Choisir un dossier…")
        self.choose_btn.clicked.connect(self.choose_folder)
        self.export_btn = QPushButton("Exporter en CSV")
        self.export_btn.setObjectName("secondary")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)
        self.folder_label = QLabel("Aucun dossier sélectionné")
        self.folder_label.setObjectName("pathLabel")
        row.addWidget(self.choose_btn)
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

        self.chart = FuelChart()
        splitter.addWidget(self.chart)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir un dossier contenant des CSV")
        if folder:
            self.start_scan(folder)

    def start_scan(self, folder):
        self.folder_label.setText(folder)
        self.table.setRowCount(0)
        self.results_by_row.clear()
        self.export_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.choose_btn.setEnabled(False)

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
        self.results_by_row[row] = result

        filename = result.get("filename") or os.path.basename(result["csv_path"])
        self.table.setItem(row, COL_FILE, QTableWidgetItem(filename))

        if result.get("error"):
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("Erreur"))
            self.table.setItem(row, COL_EVENTS, NumericItem(-1))
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(result["error"]))
        elif result["has_theft"]:
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("⚠️ Suspect"))
            self.table.setItem(row, COL_EVENTS, NumericItem(result["n_events"]))
            first_ts = result["events"][0]["ts_start"] if result["events"] else ""
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(first_ts))
        else:
            self.table.setItem(row, COL_STATUS, QTableWidgetItem("✅ Normal"))
            self.table.setItem(row, COL_EVENTS, NumericItem(0))
            self.table.setItem(row, COL_FIRST_ALERT, QTableWidgetItem(""))

    def on_finished(self):
        self.progress.setVisible(False)
        self.choose_btn.setEnabled(True)
        self.export_btn.setEnabled(self.table.rowCount() > 0)

    def on_row_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        result = self.results_by_row.get(row)
        if not result or result.get("error"):
            self.chart.clear()
            return
        # le résultat stocké lors du scan contient déjà tout ce qu'il faut pour le graphique
        self.chart.plot(result)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter les résultats", "resultats_scan.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["fichier", "statut", "nb_periodes_suspectes", "premiere_alerte"])
            for row in range(self.table.rowCount()):
                writer.writerow([
                    self.table.item(row, COL_FILE).text(),
                    self.table.item(row, COL_STATUS).text(),
                    self.table.item(row, COL_EVENTS).text(),
                    self.table.item(row, COL_FIRST_ALERT).text(),
                ])
