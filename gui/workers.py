"""
Threads d'arrière-plan (QThread) pour que l'interface reste fluide pendant
qu'un fichier ou un dossier entier est en train d'être analysé.
"""

from PySide6.QtCore import QThread, Signal

from gui.analysis import analyze_file, find_csv_files, AnalysisError


class SingleFileWorker(QThread):
    finished_ok = Signal(dict)
    finished_error = Signal(str)

    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path

    def run(self):
        try:
            result = analyze_file(self.csv_path)
        except AnalysisError as exc:
            self.finished_error.emit(str(exc))
        except Exception as exc:  # filet de sécurité pour toute erreur imprévue
            self.finished_error.emit(f"Erreur inattendue : {exc}")
        else:
            self.finished_ok.emit(result)


class BatchScanWorker(QThread):
    progress = Signal(int, int, str)     # (fait, total, nom du fichier en cours)
    file_done = Signal(dict)              # résultat pour un fichier (ou erreur encapsulée)
    finished_all = Signal()

    def __init__(self, folder, parent=None):
        super().__init__(parent)
        self.folder = folder
        self._stop_requested = False

    def stop(self):
        self._stop_requested = True

    def run(self):
        csv_files = find_csv_files(self.folder)
        total = len(csv_files)
        for i, csv_path in enumerate(csv_files, start=1):
            if self._stop_requested:
                break
            self.progress.emit(i, total, csv_path)
            try:
                result = analyze_file(csv_path)
                result["error"] = None
            except AnalysisError as exc:
                result = {"csv_path": csv_path, "filename": csv_path, "error": str(exc)}
            except Exception as exc:
                result = {"csv_path": csv_path, "filename": csv_path, "error": f"Erreur inattendue : {exc}"}
            self.file_done.emit(result)
        self.finished_all.emit()
