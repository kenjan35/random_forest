import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QListWidgetItem, QMessageBox

from gui.cursor_utils import set_button_busy, set_button_enabled
from gui.export import event_list_label, tagged_events, write_events_csv
from gui.workers import SingleFileWorker


def is_running(self):
    return self.worker is not None and self.worker.isRunning()


def set_selected_file(self, path):
    self.selected_path = path
    self.path_label.setText(os.path.basename(path))
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
        self.status_icon.setPixmap(QPixmap("assets/icons/warn.svg").scaled(
            20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        count = result["n_events"]
        self.status_label.setText(
            f"{count} période{'s' if count != 1 else ''} "
            f"suspecte{'s' if count != 1 else ''} détectée{'s' if count != 1 else ''}"
        )
    elif result.get("has_sensor_glitch"):
        self.status_label.setStyleSheet(
            "background-color:#ff9966; color:#ffffff; border-radius:10px; padding:6px 12px; font-weight:700;"
        )
        self.status_icon.setPixmap(QPixmap("assets/icons/warn_2.svg").scaled(
            20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.status_label.setText("Data incomplete")
    else:
        self.status_label.setStyleSheet(
            "background-color:#166534; color:#bbf7d0; border-radius:10px; padding:6px 12px; font-weight:700;"
        )
        self.status_icon.setPixmap(QPixmap("assets/icons/check.svg").scaled(
            20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.status_label.setText("Aucun vol détecté")

    self.events_list.clear()
    for event, label in tagged_events(result):
        self.events_list.addItem(QListWidgetItem(event_list_label(event, label)))
    self.chart.plot(result)


def export_csv(self):
    if not self.current_result:
        return
    path, _ = self._get_export_path()
    if not path:
        return
    try:
        write_events_csv(path, [self.current_result], mapping_key="filename")
    except OSError as exc:
        QMessageBox.warning(
            self,
            "Export CSV",
            f"Impossible d'écrire le fichier (est-il ouvert dans Excel ?)\n{exc}",
        )
