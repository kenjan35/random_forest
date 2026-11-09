"""
Threads d'arrière-plan (QThread) pour que l'interface reste fluide pendant
qu'un fichier ou un dossier entier est en train d'être analysé.
"""

from PySide6.QtCore import QThread, Signal

from gui.workers_data_utils import analyze_extracted_rows, open_site_from_sidebar
from gui.workers_extraction_utils import extract_site_rows, extract_site_rows_impl
from gui.workers_network_utils import install_response_capture, wait_for_captured_response
from gui.workers_run_utils import batch_scan_run, batch_stop, single_file_run
from gui.workers_selenium_run_utils import selenium_run


class SingleFileWorker(QThread):
    finished_ok = Signal(dict)
    finished_error = Signal(str)

    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.csv_path = csv_path

    run = single_file_run


class BatchScanWorker(QThread):
    progress = Signal(int, int, str)
    file_done = Signal(dict)
    finished_all = Signal()

    def __init__(self, folder, parent=None):
        super().__init__(parent)
        self.folder = folder
        self._stop_requested = False

    stop = batch_stop
    run = batch_scan_run


class SeleniumExtractionWorker(QThread):
    finished_ok = Signal(list)
    result_ready = Signal(dict)
    finished_error = Signal(str)
    dates_adjusted = Signal(str, str)

    def __init__(self, url, user_id, password, start_date, end_date, sites, parent=None):
        super().__init__(parent)
        self.url, self.user_id, self.password = url, user_id, password
        self.start_date, self.end_date = start_date, end_date
        self.sites = sites

    run = selenium_run

    _extract_site_rows = extract_site_rows
    _extract_site_rows_impl = extract_site_rows_impl
    _install_response_capture = staticmethod(install_response_capture)
    _wait_for_captured_response = staticmethod(wait_for_captured_response)
    _analyze_extracted_rows = staticmethod(analyze_extracted_rows)
    _open_site_from_sidebar = staticmethod(open_site_from_sidebar)
