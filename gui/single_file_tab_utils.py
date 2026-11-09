from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QSplitter,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gui.chart import FuelChart
from gui.cursor_utils import apply_pointer_cursor


def build_ui(self):
    root = QVBoxLayout(self)
    root.setContentsMargins(16, 16, 16, 16)
    root.setSpacing(12)

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


def drag_enter_event(self, event):
    if event.mimeData().hasUrls():
        urls = event.mimeData().urls()
        if any(u.toLocalFile().lower().endswith(".csv") for u in urls):
            self.drop_zone.setProperty("dragActive", "true")
            self.style().unpolish(self.drop_zone)
            self.style().polish(self.drop_zone)
            event.acceptProposedAction()


def drag_leave_event(self, *_):
    self.drop_zone.setProperty("dragActive", "false")
    self.style().unpolish(self.drop_zone)
    self.style().polish(self.drop_zone)


def drop_event(self, event):
    self.drop_zone.setProperty("dragActive", "false")
    self.style().unpolish(self.drop_zone)
    self.style().polish(self.drop_zone)
    urls = event.mimeData().urls()
    csv_paths = [u.toLocalFile() for u in urls if u.toLocalFile().lower().endswith(".csv")]
    if csv_paths:
        self.set_selected_file(csv_paths[0])


def browse_file(self):
    path, _ = QFileDialog.getOpenFileName(self, "Choisir un fichier CSV", "", "CSV (*.csv)")
    if path:
        self.set_selected_file(path)
