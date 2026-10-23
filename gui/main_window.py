import os

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QCursor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMessageBox, QPushButton, QApplication, QWidget,
    QHBoxLayout, QLabel, QGraphicsOpacityEffect, QStackedWidget, QVBoxLayout
)

from gui.single_file_tab import SingleFileTab
from gui.batch_scan_tab import BatchScanTab
from gui.selenium_tab import SeleniumTab
from gui.top_sites_tab import TopSitesTab
from gui.rms_console_tab import RmsConsoleTab
from gui.chart import FuelChart
from gui.style import DARK_STYLESHEET, LIGHT_STYLESHEET
from gui.cursor_utils import apply_pointer_cursor
from src.config import MODEL_PATH
THEME_TRANSITION_MS = 150
SIDEBAR_COLLAPSED_WIDTH = 68


class Sidebar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_COLLAPSED_WIDTH)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Détection de vol de carburant")
        self.resize(1200, 750)
        self.dark_mode = False
        self._theme_transition_overlay = None
        self._theme_transition_anim = None

        sidebar = Sidebar()
        self._sidebar = sidebar
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(7, 16, 7, 10)
        sidebar_layout.setSpacing(6)

        brand = QLabel()
        brand.setObjectName("sidebarBrand")
        brand.setPixmap(QPixmap("assets/icon.ico").scaled(
            28,
            28,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        brand.setFixedSize(32, 32)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(brand, alignment=Qt.AlignmentFlag.AlignHCenter)
        sidebar_layout.addSpacing(18)

        views = QStackedWidget()
        view_buttons = []

        direct_analysis = QTabWidget()
        direct_analysis.addTab(SingleFileTab(), "Analyser un fichier")
        direct_analysis.addTab(BatchScanTab(), "Scanner un dossier")
        direct_analysis.tabBar().setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        extraction_view = SeleniumTab()
        dashboard_view = TopSitesTab()
        extraction_view.history_updated.connect(dashboard_view.refresh)
        views.addWidget(dashboard_view)
        views.addWidget(extraction_view)
        views.addWidget(direct_analysis)
        views.addWidget(RmsConsoleTab())

        for label, icon_name, selected_icon_name, index in (
            ("Dashboard", "dashboard.svg", "dashboard-white.svg", 0),
            ("Extraction Power-Noc", "data.svg", "data-white.svg", 1),
            ("Analyse direct", "analysis.svg", "analysis-white.svg", 2),
            ("Extraction API RMS", "upload.svg", "upload-white.svg", 3),
        ):
            button = QPushButton(label)
            button.setObjectName("sidebarButton")
            button.setIcon(QIcon(os.path.join("assets", "icons", icon_name)))
            button.setIconSize(QSize(32, 32))
            button.setFixedSize(52, 52)
            button.setContentsMargins(0, 0, 0, 0)
            button.setProperty("compact", True)
            button.style().unpolish(button)
            button.style().polish(button)
            button.setText("")
            button.setToolTip(label)
            button.default_icon = icon_name
            button.selected_icon = selected_icon_name
            button.dark_icon = selected_icon_name
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked, selected_index=index: self._select_view_and_update(
                    views, view_buttons, selected_index
                )
            )
            apply_pointer_cursor(button)
            sidebar_layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            view_buttons.append(button)
        sidebar_layout.addStretch()
        view_buttons[0].setChecked(True)
        self._view_buttons = view_buttons
        self._selected_view_index = 0

        self._update_sidebar_icons(view_buttons, 0, self.dark_mode)

        self.theme_btn = QPushButton()
        self._update_theme_button()
        self.theme_btn.setObjectName("themeToggle")
        self.theme_btn.setFixedWidth(38)
        self.theme_btn.setFixedHeight(38)
        self.theme_btn.clicked.connect(self.toggle_theme)
        apply_pointer_cursor(self.theme_btn)

        theme_btn_container = QWidget()
        theme_btn_container.setObjectName("themeToggleContainer")
        theme_btn_container.setFixedHeight(50)
        theme_btn_container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        theme_btn_layout = QHBoxLayout(theme_btn_container)
        theme_btn_layout.setContentsMargins(0, 4, 0, 4)
        theme_btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        theme_btn_layout.addWidget(self.theme_btn)
        sidebar_layout.addWidget(theme_btn_container)
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(sidebar)
        content_layout.addWidget(views, stretch=1)
        self.setCentralWidget(content)

        if not os.path.exists(MODEL_PATH):
            QMessageBox.warning(
                self,
                "Modèle non trouvé",
                "'model/random_forest.pkl' est introuvable.\n\n"
                "Lancez d'abord `python main.py` à la racine du projet pour "
                "entraîner et sauvegarder le modèle avant d'utiliser cette interface.",
            )

    @staticmethod
    def _update_sidebar_icons(buttons, selected_index, dark_mode=False):
        for index, button in enumerate(buttons):
            icon_name = (
                button.selected_icon
                if index == selected_index or dark_mode
                else button.default_icon
            )
            button.setIcon(QIcon(os.path.join("assets", "icons", icon_name)))

    def _select_view_and_update(self, stack, buttons, index):
        self._select_view(stack, buttons, index)
        self._selected_view_index = index
        self._update_sidebar_icons(buttons, index, self.dark_mode)

    @staticmethod
    def _select_view(stack, buttons, index):
        stack.setCurrentIndex(index)
        for button_index, button in enumerate(buttons):
            button.setChecked(button_index == index)

    def _update_theme_button(self):
        if self.dark_mode:
            self.theme_btn.setIcon(QIcon("assets/icons/sun-white.svg"))
        else:
            self.theme_btn.setIcon(QIcon("assets/icons/moon.svg"))

    def toggle_theme(self):
        snapshot = self.grab()

        self.dark_mode = not self.dark_mode

        app = QApplication.instance()
        app.setStyleSheet(DARK_STYLESHEET if self.dark_mode else LIGHT_STYLESHEET)

        self._update_theme_button()
        self._update_sidebar_icons(
            self._view_buttons, self._selected_view_index, self.dark_mode
        )

        for chart in self.findChildren(FuelChart):
            chart.set_theme(self.dark_mode)
        for top_sites in self.findChildren(TopSitesTab):
            top_sites.set_theme(self.dark_mode)
        for console in self.findChildren(RmsConsoleTab):
            console.set_theme(self.dark_mode)

        self._play_theme_transition(snapshot)

    def _play_theme_transition(self, snapshot):
        """
        Qt n'anime pas les couleurs QSS directement (changer toute la
        feuille de style est instantané). Pour donner l'impression d'une
        transition douce, on superpose une capture de l'ancien thème et on
        la fait disparaitre en fondu : le nouveau thème, déjà appliqué en
        dessous, apparait progressivement.
        """
        overlay = QLabel(self)
        overlay.setPixmap(snapshot)
        overlay.setGeometry(self.rect())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        overlay.show()
        overlay.raise_()
 
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)
 
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(THEME_TRANSITION_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(overlay.deleteLater)
 
        # garde une reference : sans ca, le garbage collector Python peut
        # detruire l'animation avant qu'elle ne soit terminee
        self._theme_transition_overlay = overlay
        self._theme_transition_anim = anim
        anim.start()