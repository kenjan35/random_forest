import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QSplitter, QMessageBox
)

from gui.chart import FuelChart
from gui.workers import SingleFileWorker
from gui.export import tagged_events, event_list_label, write_events_csv
from gui.cursor_utils import apply_pointer_cursor, set_button_enabled, set_button_busy


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
        apply_pointer_cursor(self.browse_btn)
        self.analyze_btn = QPushButton("Analyser")
        self.analyze_btn.setEnabled(False)
        self.analyze_btn.clicked.connect(self.run_analysis)
        apply_pointer_cursor(self.analyze_btn)
        self.export_btn = QPushButton("Exporter en CSV")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self.export_csv)
        apply_pointer_cursor(self.export_btn)
        self.path_label = QLabel("Aucun fichier sélectionné")
        self.path_label.setObjectName("pathLabel")
        row.addWidget(self.browse_btn)
        row.addWidget(self.analyze_btn)
        row.addWidget(self.export_btn)
        row.addWidget(self.path_label, stretch=1)
        root.addLayout(row)

        # zone resultats : liste des periodes + graphique cote a cote
        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(20, 20)
        self.status_icon.setAlignment(Qt.AlignCenter)

        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        status_layout.addWidget(self.status_icon)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        left_layout.addLayout(status_layout)
        # left_layout.setSpacing(6)
        title = QLabel("Période(s) suspecte(s)")
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

    def _is_running(self):
        return self.worker is not None and self.worker.isRunning()

    def set_selected_file(self, path):
        self.selected_path = path
        self.path_label.setText(os.path.basename(path))
        # ne réactive pas le bouton pendant une analyse : lancer un second
        # thread détruirait le premier en cours d'exécution
        if not self._is_running():
            set_button_enabled(self.analyze_btn, True)

    def run_analysis(self):
        if not self.selected_path or self._is_running():
            return
        self.analyze_btn.setFixedWidth(150)
        self.analyze_btn.setText("Analyse en cours")
        set_button_busy(self.analyze_btn, True)
        set_button_enabled(self.analyze_btn, False)

        self.events_list.clear()
        self.status_label.setText("")
        self.status_icon.clear()
        self.status_label.clear()

        self.worker = SingleFileWorker(self.selected_path)
        self.worker.finished_ok.connect(self.on_success)
        self.worker.finished_error.connect(self.on_error)
        self.worker.start()

    def on_success(self, result):
        self.current_result = result

        self._reset_analyze_button()
        set_button_enabled(self.export_btn, bool(result))
        if result["has_theft"]:
            self.status_label.setStyleSheet(
                "background-color:#7f1d1d; color:#fecaca; border-radius:10px; padding:6px 12px; font-weight:700;"
            )
            self.status_icon.setPixmap(
                QPixmap("assets/icons/warn.svg").scaled(
                    20,
                    20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
            if result['n_events'] == 1 :
                self.status_label.setText(f"{result['n_events']} période suspecte détectée")
            else :
                self.status_label.setText(f"{result['n_events']} périodes suspectes détectées")
        elif result.get("has_sensor_glitch"):
            self.status_label.setStyleSheet(
                "background-color:#ff9966; color:#ffffff; border-radius:10px; padding:6px 12px; font-weight:700;"
            )
            self.status_icon.setPixmap(
                QPixmap("assets/icons/warn_2.svg").scaled(
                    20,
                    20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
            self.status_label.setText("Data incomplete")
        else:
            self.status_label.setStyleSheet(
                "background-color:#166534; color:#bbf7d0; border-radius:10px; padding:6px 12px; font-weight:700;"
            )
            self.status_icon.setPixmap(
                QPixmap("assets/icons/check.svg").scaled(
                    20,
                    20,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )

            self.status_label.setText("Aucun vol détecté")

        self.events_list.clear()
        for ev, label in tagged_events(result):
            self.events_list.addItem(QListWidgetItem(event_list_label(ev, label)))

        self.chart.plot(result)

    def export_csv(self):
        if not self.current_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter les résultats", "resultat_scan.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            write_events_csv(path, [self.current_result], mapping_key="filename")
        except OSError as exc:
            QMessageBox.warning(self, "Export CSV", f"Impossible d'écrire le fichier (est-il ouvert dans Excel ?)\n{exc}")

    def _reset_analyze_button(self):
        set_button_busy(self.analyze_btn, False)
        set_button_enabled(self.analyze_btn, bool(self.selected_path))
        self.analyze_btn.setText("Analyser")
        # annule le setFixedWidth(150) posé au lancement
        self.analyze_btn.setMinimumWidth(0)
        self.analyze_btn.setMaximumWidth(16777215)
        self.analyze_btn.adjustSize()

    def on_error(self, message):
        self._reset_analyze_button()
        self.status_label.setStyleSheet(
            "background-color:#78350f; color:#fde68a; border-radius:10px; padding:6px 12px; font-weight:700;"
        )
        self.status_label.setText("Erreur pendant l'analyse")
        QMessageBox.warning(self, "Erreur", message)
