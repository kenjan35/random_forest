from PySide6.QtWidgets import QFileDialog, QMessageBox

from gui.cursor_utils import set_button_busy, set_button_enabled


def get_export_path(self):
    return QFileDialog.getSaveFileName(
        self, "Exporter les résultats", "resultat_scan.csv", "CSV (*.csv)"
    )


def reset_analyze_button(self):
    set_button_busy(self.analyze_btn, False)
    set_button_enabled(self.analyze_btn, bool(self.selected_path))
    self.analyze_btn.setText("Analyser")
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
