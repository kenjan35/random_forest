import os

from gui.analysis import AnalysisError, analyze_file, find_csv_files


def single_file_run(self):
    try:
        result = analyze_file(self.csv_path)
    except AnalysisError as exc:
        self.finished_error.emit(str(exc))
    except Exception as exc:
        self.finished_error.emit(f"Erreur inattendue : {exc}")
    else:
        self.finished_ok.emit(result)


def batch_stop(self):
    self._stop_requested = True


def batch_scan_run(self):
    csv_files = find_csv_files(self.folder)
    total = len(csv_files)
    for index, csv_path in enumerate(csv_files, start=1):
        if self._stop_requested:
            break
        filename = os.path.basename(csv_path)
        try:
            result = analyze_file(csv_path)
            result["error"] = None
        except AnalysisError as exc:
            result = {"csv_path": csv_path, "filename": filename, "error": str(exc)}
        except Exception as exc:
            result = {
                "csv_path": csv_path,
                "filename": filename,
                "error": f"Erreur inattendue : {exc}",
            }
        self.file_done.emit(result)
        self.progress.emit(index, total, csv_path)
    self.finished_all.emit()
