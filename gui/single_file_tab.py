import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter, QMessageBox
)

from gui.chart import FuelChart
from gui.workers import SingleFileWorker


class SingleFileTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.worker = None
        self.current_result = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # zone glisser-déposer
        self.drop_zone = QLabel("Glissez un fichier CSV ici\nou cliquez sur \"Choisir un fichier\"")
        self.drop_zone.setObjectName("dropZone")
        self.drop_zone.setAlignment(Qt.AlignCenter)
        root.addWidget(self.drop_zone)

        row = QHBoxLayout()
        self.browse_btn = QPushButton("Choisir un fichier…")
        self.browse_btn.clicked.connect(self.browse_file)
        self.analyze_btn = QPushButton("Analyser")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.path_label = QLabel("Aucun fichier sélectionné")
        self.path_label.setObjectName("pathLabel")
        row.addWidget(self.browse_btn)
        row.addWidget(self.analyze_btn)
        row.addWidget(self.path_label, stretch=1)
        root.addLayout(row)

        # zone resultats : liste des periodes + graphique cote a cote
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.status_label = QLabel("")
        left_layout.addWidget(self.status_label)
        title = QLabel("Périodes suspectes")
        title.setObjectName("sectionTitle")
        left_layout.addWidget(title)
        self.events_list = QListWidget()
        left_layout.addWidget(self.events_list)

        self.chart = FuelChart()

        splitter.addWidget(left)
        splitter.addWidget(self.chart)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        self.selected_path = None

    # --- glisser-deposer ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith(".csv") for u in urls):
                self.drop_zone.setProperty("dragActive", "true")
                self.style().unpolish(self.drop_zone)
                self.style().polish(self.drop_zone)
                event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_zone.setProperty("dragActive", "false")
        self.style().unpolish(self.drop_zone)
        self.style().polish(self.drop_zone)

    def dropEvent(self, event):
        self.drop_zone.setProperty("dragActive", "false")
        self.style().unpolish(self.drop_zone)
        self.style().polish(self.drop_zone)
        urls = event.mimeData().urls()
        csv_paths = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith(".csv")]
        if csv_paths:
            self.set_selected_file(csv_paths[0])

    # --- selection / lancement ---
    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier CSV", "", "CSV (*.csv)")
        if path:
            self.set_selected_file(path)

    def set_selected_file(self, path):
        self.selected_path = path
        self.path_label.setText(os.path.basename(path))
        self.analyze_btn.setEnabled(True)

    def run_analysis(self):
        if not self.selected_path:
            return
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.setText("Analyse en cours…")
        self.events_list.clear()
        self.status_label.setText("")

        self.worker = SingleFileWorker(self.selected_path)
        self.worker.finished_ok.connect(self.on_success)
        self.worker.finished_error.connect(self.on_error)
        self.worker.start()

    def on_success(self, result):
        self.current_result = result
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyser")

        if result["has_theft"]:
            self.status_label.setStyleSheet(
                "background-color:#7f1d1d; color:#fecaca; border-radius:10px; padding:6px 12px; font-weight:700;"
            )
            self.status_label.setText(f"⚠️  {result['n_events']} période(s) suspecte(s) détectée(s)")
        else:
            self.status_label.setStyleSheet(
                "background-color:#166534; color:#bbf7d0; border-radius:10px; padding:6px 12px; font-weight:700;"
            )
            self.status_label.setText("✅ Aucun vol détecté")

        self.events_list.clear()
        for ev in result["events"]:
            item = QListWidgetItem(f'Lignes {ev["row_start"]}-{ev["row_end"]}\n{ev["ts_start"]}  →  {ev["ts_end"]}')
            self.events_list.addItem(item)

        self.chart.plot(result)

    def on_error(self, message):
        self.analyze_btn.setEnabled(True)
        self.analyze_btn.setText("Analyser")
        self.status_label.setStyleSheet(
            "background-color:#78350f; color:#fde68a; border-radius:10px; padding:6px 12px; font-weight:700;"
        )
        self.status_label.setText("Erreur pendant l'analyse")
        QMessageBox.warning(self, "Erreur", message)
