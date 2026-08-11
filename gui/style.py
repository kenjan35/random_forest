# Palette d'accent (dérivée de #1caae2, demandée pour boutons/onglets/etc.)
# ACCENT       : couleur de base
# ACCENT_HOVER : plus claire, pour le survol en mode sombre
# ACCENT_LIGHT : teinte plus claire, pour du texte/liens sur fond sombre
# ACCENT_DARK  : plus foncée, pour le survol en mode clair et l'état "pressed"
# ACCENT_DARKER: encore plus foncée, pour l'état "pressed" en mode clair

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1b1e24;
    color: #e6e8ec;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #2f333c;
    border-radius: 8px;
    background-color: #22252c;
    top: -1px;
}

QTabBar::tab {
    background-color: #2a2d36;
    color: #9199a6;
    padding: 10px 22px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #22252c;
    color: #f1f3f6;
    border-bottom: 2px solid #1caae2;
}

QPushButton {
    background-color: #1caae2;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #3fbde9;
}

QPushButton:pressed {
    background-color: #1690bd;
}

QPushButton:disabled {
    background-color: #3a3e48;
    color: #6b7280;
}

QPushButton#secondary {
    background-color: #2a2d36;
    color: #e6e8ec;
    border: 1px solid #3a3e48;
}

QPushButton#secondary:hover {
    background-color: #343842;
}

QPushButton#secondary:disabled {
    background-color: #2a2d36;
    color: #565b66;
    border: 1px solid #2f333c;
}

QPushButton#themeToggle {
    background-color: transparent;
    border: 1px solid #3a3e48;
    border-radius: 6px;
    padding: 8px 18px 8px 14px;
    font-weight: 600;
    color: #e6e8ec;
}

QPushButton#themeToggle:hover {
    background-color: #2a2d36;
}

QLabel#dropZone {
    border: 2px dashed #3a3e48;
    border-radius: 10px;
    padding: 40px;
    color: #7d8592;
    font-size: 14px;
}

QLabel#dropZone[dragActive="true"] {
    border-color: #1caae2;
    color: #8ddcf0;
    background-color: rgba(28, 170, 226, 0.08);
}

QLabel#pathLabel {
    color: #8ddcf0;
    font-weight: 600;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f1f3f6;
}

QTableWidget {
    background-color: #22252c;
    alternate-background-color: #272a32;
    gridline-color: #2f333c;
    border: 1px solid #2f333c;
    border-radius: 6px;
    selection-background-color: #1690bd;
    selection-color: white;
}

QHeaderView::section {
    background-color: #2a2d36;
    color: #c4cad4;
    padding: 8px;
    border: none;
    border-right: 1px solid #1b1e24;
    font-weight: 600;
}

QHeaderView::section:last {
    border-right: none;
}

QProgressBar {
    border: 1px solid #3a3e48;
    border-radius: 6px;
    text-align: center;
    background-color: #2a2d36;
    color: #e6e8ec;
}

QProgressBar::chunk {
    background-color: #1caae2;
    border-radius: 5px;
}

QListWidget {
    background-color: #22252c;
    border: 1px solid #2f333c;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
}

QListWidget::item:selected {
    background-color: #1690bd;
}

QTableCornerButton::section {
    background-color: #2a2d36;
    border: none;
    border-right: 1px solid #1b1e24;
    border-bottom: 1px solid #1b1e24;
}

QTableCornerButton::section:hover {
    background-color: #3a3e48;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px 2px 2px 0;
}

QScrollBar::handle:vertical {
    background: #3a3e48;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #4a4f5b;
}

QScrollBar::handle:vertical:pressed {
    background: #1caae2;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    border: none;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 0 2px 2px 2px;
}

QScrollBar::handle:horizontal {
    background: #3a3e48;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #4a4f5b;
}

QScrollBar::handle:horizontal:pressed {
    background: #1caae2;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    border: none;
    background: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

#badgeOk {
    background-color: #1e4030;
    color: #b8e6cc;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeAlert {
    background-color: #4a2323;
    color: #f2c6c6;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeError {
    background-color: #453419;
    color: #f0dba8;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}
"""

LIGHT_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background-color: #ffffff;
    top: -1px;
}

QTabBar::tab {
    background-color: #e2e8f0;
    color: #64748b;
    padding: 10px 22px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 2px solid #1caae2;
}

QPushButton {
    background-color: #1caae2;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 9px 18px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1690bd;
}

QPushButton:pressed {
    background-color: #12759a;
}

QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

QPushButton#secondary {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
}

QPushButton#secondary:hover {
    background-color: #f1f5f9;
}

QPushButton#secondary:disabled {
    background-color: #f1f5f9;
    color: #b0b8c4;
    border: 1px solid #e2e8f0;
}

QPushButton#themeToggle {
    background-color: transparent;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px 18px 8px 14px;
    font-weight: 600;
    color: #0f172a;
}

QPushButton#themeToggle:hover {
    background-color: #e2e8f0;
}

QLabel#dropZone {
    border: 2px dashed #cbd5e1;
    border-radius: 10px;
    padding: 40px;
    color: #64748b;
    font-size: 14px;
}

QLabel#dropZone[dragActive="true"] {
    border-color: #1caae2;
    color: #0f8bc0;
    background-color: rgba(28, 170, 226, 0.06);
}

QLabel#pathLabel {
    color: #0f8bc0;
    font-weight: 600;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #0f172a;
}

QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    gridline-color: #e2e8f0;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    selection-background-color: #1caae2;
    selection-color: white;
}

QHeaderView::section {
    background-color: #e2e8f0;
    color: #334155;
    padding: 8px;
    border: none;
    border-right: 1px solid #cbd5e1;
    font-weight: 600;
}

QHeaderView::section:last {
    border-right: none;
}

QProgressBar {
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    text-align: center;
    background-color: #e2e8f0;
    color: #0f172a;
}

QProgressBar::chunk {
    background-color: #1caae2;
    border-radius: 5px;
}

QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 4px;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    color: #0f172a;
}

QListWidget::item:selected {
    background-color: #1caae2;
    color: white;
}

QTableCornerButton::section {
    background-color: #e2e8f0;
    border: none;
    border-right: 1px solid #cbd5e1;
    border-bottom: 1px solid #cbd5e1;
}

QTableCornerButton::section:hover {
    background-color: #cbd5e1;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px 2px 2px 0;
}

QScrollBar::handle:vertical {
    background: #cbd5e1;
    border-radius: 5px;
    min-height: 24px;
}

QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}

QScrollBar::handle:vertical:pressed {
    background: #1caae2;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    border: none;
    background: none;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 0 2px 2px 2px;
}

QScrollBar::handle:horizontal {
    background: #cbd5e1;
    border-radius: 5px;
    min-width: 24px;
}

QScrollBar::handle:horizontal:hover {
    background: #94a3b8;
}

QScrollBar::handle:horizontal:pressed {
    background: #1caae2;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
    border: none;
    background: none;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
}

#badgeOk {
    background-color: #dcfce7;
    color: #166534;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeAlert {
    background-color: #fee2e2;
    color: #991b1b;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}

#badgeError {
    background-color: #fef3c7;
    color: #92400e;
    border-radius: 10px;
    padding: 4px 12px;
    font-weight: 700;
}
"""

# alias conserve pour compatibilite (ancien nom utilise par gui_app.py)
STYLESHEET = DARK_STYLESHEET