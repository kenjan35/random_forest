STYLESHEET = """
QMainWindow, QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #111827;
    top: -1px;
}

QTabBar::tab {
    background-color: #1e293b;
    color: #94a3b8;
    padding: 10px 22px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #111827;
    color: #f8fafc;
    border-bottom: 2px solid #3b82f6;
}

QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3b82f6;
}

QPushButton:pressed {
    background-color: #1d4ed8;
}

QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}

QPushButton#secondary {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
}

QPushButton#secondary:hover {
    background-color: #334155;
}

QLabel#dropZone {
    border: 2px dashed #334155;
    border-radius: 10px;
    padding: 40px;
    color: #64748b;
    font-size: 14px;
}

QLabel#dropZone[dragActive="true"] {
    border-color: #3b82f6;
    color: #93c5fd;
    background-color: rgba(59, 130, 246, 0.08);
}

QLabel#pathLabel {
    color: #93c5fd;
    font-weight: 600;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f8fafc;
}

QTableWidget {
    background-color: #111827;
    alternate-background-color: #16202f;
    gridline-color: #1e293b;
    border: 1px solid #1e293b;
    border-radius: 6px;
    selection-background-color: #1d4ed8;
    selection-color: white;
}

QHeaderView::section {
    background-color: #1e293b;
    color: #cbd5e1;
    padding: 8px;
    border: none;
    font-weight: 600;
}

QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    text-align: center;
    background-color: #1e293b;
    color: #e2e8f0;
}

QProgressBar::chunk {
    background-color: #3b82f6;
    border-radius: 5px;
}

QListWidget {
    background-color: #111827;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #1d4ed8;
}

QScrollBar:vertical {
    background: #0f172a;
    width: 10px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 5px;
    min-height: 20px;
}

#badgeOk {
    background-color: #166534;
    color: #bbf7d0;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeAlert {
    background-color: #7f1d1d;
    color: #fecaca;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeError {
    background-color: #78350f;
    color: #fde68a;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}
"""
