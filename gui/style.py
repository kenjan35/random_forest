# Palette d'accent (dérivée de #1caae2, demandée pour boutons/onglets/etc.)
# ACCENT       : couleur de base
# ACCENT_HOVER : plus claire, pour le survol en mode sombre
# ACCENT_LIGHT : teinte plus claire, pour du texte/liens sur fond sombre
# ACCENT_DARK  : plus foncée, pour le survol en mode clair et l'état "pressed"
# ACCENT_DARKER: encore plus foncée, pour l'état "pressed" en mode clair

DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #3e3e42;
    color: #e6e8ec;
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}

QWidget#sidebar {
    background-color: #292a2e;
    border-right: 1px solid #52535a;
}

QWidget#themeToggleContainer {
    background-color: transparent;
}

QFrame#metricCard {
    background-color: #3e3e42;
    border: 1px solid #5d5e66;
    border-radius: 10px;
}

QFrame#metricCard:hover {
    border-color: #1caae2;
    background-color: #45454a;
}

/* La règle globale "QWidget { background-color }" donne aux libellés leur propre
   fond : sans ceci, ils restent de l'ancienne couleur quand la carte change au survol. */
QFrame#metricCard QLabel {
    background-color: transparent;
}

QLabel#metricCaption {
    color: #aeb5c0;
    font-size: 12px;
    font-weight: 600;
}

QLabel#metricValueSites { color: #38bdf8; font-size: 24px; font-weight: 800; }
QLabel#metricValueEvents { color: #f59e0b; font-size: 24px; font-weight: 800; }
QLabel#metricValueFuel { color: #fb7185; font-size: 24px; font-weight: 800; }
QLabel#metricValuePeak { color: #a78bfa; font-size: 24px; font-weight: 800; }

QPushButton#sidebarToggle {
    background-color: transparent;
    color: #aeb5c0;
    border: none;
    padding: 8px;
}

QPushButton#sidebarToggle:hover {
    background-color: #3e4249;
}

QLabel#sidebarBrand {
    color: #8ddcf0;
    font-size: 15px;
    font-weight: 800;
}

QPushButton#sidebarButton {
    background-color: transparent;
    color: #aeb5c0;
    border: none;
    border-radius: 6px;
    padding: 2px;
    text-align: left;
    font-weight: 600;
}

QPushButton#sidebarButton[expanded="false"] {
    text-align: center;
}

QPushButton#sidebarButton[expanded="true"] {
    text-align: left;
}

QPushButton#sidebarButton[compact="true"] {
    text-align: center;
    padding: 2px;
}

QPushButton#sidebarButton:hover {
    background-color: #3e4249;
    color: #f1f3f6;
}

QPushButton#sidebarButton:checked {
    background-color: #1caae2;
    color: white;
}

QLabel#pageTitle {
    font-size: 22px;
    font-weight: 700;
    color: #f1f3f6;
}

QLabel#mutedLabel {
    color: #9aa3b1;
}

QGroupBox {
    border: 1px solid #52535a;
    border-radius: 7px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}

QLineEdit, QDateEdit {
    background-color: #45454a;
    border: 1px solid #5d5e66;
    border-radius: 5px;
    padding: 8px;
    color: #e6e8ec;
}

QLineEdit:focus, QDateEdit:focus {
    border-color: #1caae2;
}

QCalendarWidget {
    background-color: #45454a;
    color: #e6e8ec;
}

QCalendarWidget QWidget {
    background-color: #45454a;
    color: #e6e8ec;
}

QCalendarWidget QToolButton {
    color: #e6e8ec;
    background-color: #45454a;
    border: none;
    padding: 4px;
}

QCalendarWidget QAbstractItemView {
    background-color: #45454a;
    color: #e6e8ec;
    selection-background-color: #1caae2;
    selection-color: white;
}

QCalendarWidget QTableView {
    background-color: #45454a;
    color: #e6e8ec;
    gridline-color: #52535a;
    selection-background-color: #1caae2;
    selection-color: white;
}

QCalendarWidget QHeaderView {
    background-color: #45454a;
}

QCalendarWidget QHeaderView::section {
    background-color: #ffffff;
    color: #000000;
    border: none;
    padding: 4px;
}

QCalendarWidget QAbstractItemView QHeaderView::section,
QCalendarWidget QAbstractItemView QHeaderView::section:disabled {
    background-color: #ffffff;
    color: #000000;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #7d8592;
}

QTabWidget::pane {
    border: 1px solid #52535a;
    border-radius: 8px;
    background-color: #45454a;
    top: -1px;
}

QTabBar::tab {
    background-color: #4d4d54;
    color: #9199a6;
    padding: 14px 22px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #45454a;
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
    background-color: #5d5e66;
    color: #6b7280;
}

QPushButton#secondary {
    background-color: #4d4d54;
    color: #e6e8ec;
    border: 1px solid #5d5e66;
}

QPushButton#secondary:hover {
    background-color: #575860;
}

QPushButton#secondary:disabled {
    background-color: #4d4d54;
    color: #565b66;
    border: 1px solid #52535a;
}

QPushButton#themeToggle {
    background-color: transparent;
    border: 1px solid #5d5e66;
    border-radius: 19px;
    padding: 0px;
    font-weight: 600;
    color: #e6e8ec;
}

QPushButton#themeToggle:hover {
    background-color: #4d4d54;
}

QLabel#dropZone {
    border: 2px dashed #5d5e66;
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
    background-color: #45454a;
    alternate-background-color: #4a4a50;
    gridline-color: #52535a;
    border: 1px solid #52535a;
    border-radius: 6px;
    selection-background-color: #1690bd;
    selection-color: white;
}

QHeaderView::section {
    background-color: #4d4d54;
    color: #c4cad4;
    padding: 8px;
    border: none;
    border-right: 1px solid #3e3e42;
    font-weight: 600;
}
 
QHeaderView::section:last {
    border-right: none;
}
 
QProgressBar {
    border: 1px solid #5d5e66;
    border-radius: 6px;
    text-align: center;
    background-color: #4d4d54;
    color: #e6e8ec;
}
 
QProgressBar::chunk {
    background-color: #1caae2;
    border-radius: 5px;
}
 
QListWidget {
    background-color: #45454a;
    border: 1px solid #52535a;
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
    background-color: #4d4d54;
    border: none;
    border-right: 1px solid #3e3e42;
    border-bottom: 1px solid #3e3e42;
}
 
QTableCornerButton::section:hover {
    background-color: #5d5e66;
}
 
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px 2px 2px 0;
}
 
QScrollBar::handle:vertical {
    background: #5d5e66;
    border-radius: 5px;
    min-height: 24px;
}
 
QScrollBar::handle:vertical:hover {
    background: #6d6f79;
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
    background: #5d5e66;
    border-radius: 5px;
    min-width: 24px;
}
 
QScrollBar::handle:horizontal:hover {
    background: #6d6f79;
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

QWidget#sidebar {
    background-color: #eef2f7;
    border-right: 1px solid #dbe3ec;
}

QWidget#themeToggleContainer {
    background-color: transparent;
}

QFrame#metricCard {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
}

QFrame#metricCard:hover {
    border-color: #1caae2;
    background-color: #ffffff;
}

/* La règle globale "QWidget { background-color }" donne aux libellés leur propre
   fond : sans ceci, ils restent de l'ancienne couleur quand la carte change au survol. */
QFrame#metricCard QLabel {
    background-color: transparent;
}

QLabel#metricCaption {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
}

QLabel#metricValueSites { color: #0284c7; font-size: 24px; font-weight: 800; }
QLabel#metricValueEvents { color: #d97706; font-size: 24px; font-weight: 800; }
QLabel#metricValueFuel { color: #e11d48; font-size: 24px; font-weight: 800; }
QLabel#metricValuePeak { color: #7c3aed; font-size: 24px; font-weight: 800; }

QPushButton#sidebarToggle {
    background-color: transparent;
    color: #526174;
    border: none;
    padding: 8px;
}

QPushButton#sidebarToggle:hover {
    background-color: #dfe8f1;
}

QLabel#sidebarBrand {
    color: #087ea4;
    font-size: 15px;
    font-weight: 800;
}

QPushButton#sidebarButton {
    background-color: transparent;
    color: #526174;
    border: none;
    border-radius: 6px;
    padding: 2px;
    text-align: left;
    font-weight: 600;
}

QPushButton#sidebarButton[expanded="false"] {
    text-align: center;
}

QPushButton#sidebarButton[expanded="true"] {
    text-align: left;
}

QPushButton#sidebarButton[compact="true"] {
    text-align: center;
    padding: 2px;
}

QPushButton#sidebarButton:hover {
    background-color: #dfe8f1;
    color: #0f172a;
}

QPushButton#sidebarButton:checked {
    background-color: #1caae2;
    color: white;
}

QLabel#pageTitle {
    font-size: 22px;
    font-weight: 700;
    font-family: "Baloo Bhaijaan";
    color: #0f172a;
}

QLabel#mutedLabel {
    color: #64748b;
}

QGroupBox {
    border: 1px solid #dbe3ec;
    border-radius: 7px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: 700;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}

QLineEdit, QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 5px;
    padding: 8px;
    color: #0f172a;
}

QLineEdit:focus, QDateEdit:focus {
    border-color: #1caae2;
}

QCalendarWidget {
    background-color: #ffffff;
    color: #0f172a;
}

QCalendarWidget QWidget {
    background-color: #ffffff;
    color: #0f172a;
}

QCalendarWidget QToolButton {
    color: #0f172a;
    background-color: #ffffff;
    border: none;
    padding: 4px;
}

QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    selection-background-color: #1caae2;
    selection-color: white;
}

QCalendarWidget QTableView {
    background-color: #ffffff;
    color: #0f172a;
    gridline-color: #e2e8f0;
    selection-background-color: #1caae2;
    selection-color: white;
}

QCalendarWidget QHeaderView {
    background-color: #ffffff;
}

QCalendarWidget QHeaderView::section {
    background-color: #ffffff;
    color: #0f172a;
    border: none;
    padding: 4px;
}

QCalendarWidget QAbstractItemView:disabled {
    color: #94a3b8;
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
    padding: 14px 22px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: 4px solid #1caae2;
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
    border-radius: 19px;
    padding: 0px;
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
STYLESHEET = LIGHT_STYLESHEET