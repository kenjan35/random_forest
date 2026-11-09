from PySide6.QtWidgets import QWidget

from gui.single_file_tab_utils import (
    browse_file,
    build_ui,
    drag_enter_event,
    drag_leave_event,
    drop_event,
)
from gui.single_file_tab_utils_1 import (
    export_csv,
    is_running,
    on_success,
    run_analysis,
    set_selected_file,
)
from gui.single_file_tab_utils_2 import (
    get_export_path,
    on_error,
    reset_analyze_button,
)


class SingleFileTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.worker = None
        self.current_result = None
        self._build_ui()

    _build_ui = build_ui
    dragEnterEvent = drag_enter_event
    dragLeaveEvent = drag_leave_event
    dropEvent = drop_event
    browse_file = browse_file
    _is_running = is_running
    set_selected_file = set_selected_file
    run_analysis = run_analysis
    on_success = on_success
    export_csv = export_csv
    _get_export_path = get_export_path
    _reset_analyze_button = reset_analyze_button
    on_error = on_error
