"""
Onglet « Console de stockage » RMS SALTEC : connexion à gauche (repliable),
navigation dans le bucket au centre, aperçu du fichier sélectionné à droite
(affiché seulement quand un fichier est sélectionné).
Toute la logique S3 est dans gui/rms_client.py.
"""

import os
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel, QByteArray, QEvent, QModelIndex, QSize, QSortFilterProxyModel, Qt,
    QThread, QTimer, Signal,
)
from PySide6.QtGui import (
    QColor, QFont, QGuiApplication, QIcon, QKeySequence, QPainter, QPixmap, QShortcut,
    QSyntaxHighlighter, QTextCharFormat,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPlainTextEdit, QProgressBar, QPushButton, QSpinBox, QSplitter, QStyle,
    QStyledItemDelegate, QTableView, QVBoxLayout, QWidget,
)

from gui import rms_client as rms
from gui.cursor_utils import apply_pointer_cursor, set_button_busy, set_button_enabled

# ---------------------------------------------------------------- apparence

# Palette alignée sur gui/style.py (mêmes couleurs, tailles et police que les autres onglets).
THEMES = {
    "light": dict(
        bg="#f8fafc", panel="#ffffff", panel_alt="#f8fafc", border="#e2e8f0", border_strong="#cbd5e1",
        input="#ffffff", text="#0f172a", muted="#64748b", faint="#94a3b8",
        accent="#1caae2", accent_text="#ffffff", accent_hover="#1690bd", accent_pressed="#12759a",
        link="#0f8bc0", selected="#1caae2", selected_text="#ffffff", hover="#f1f5f9",
        header_bg="#e2e8f0", header_text="#334155", secondary_hover="#f1f5f9",
        disabled_bg="#e2e8f0", disabled_text="#94a3b8",
        ok_bg="#dcfce7", ok_text="#166534", warn_bg="#fef3c7", warn_text="#92400e",
        error_bg="#fee2e2", error_text="#991b1b",
        json_key="#0f6f9c", json_string="#9a6700", json_number="#6d28d9", json_literal="#be185d",
    ),
    "dark": dict(
        bg="#3e3e42", panel="#45454a", panel_alt="#3e3e42", border="#52535a", border_strong="#5d5e66",
        input="#45454a", text="#e6e8ec", muted="#9aa3b1", faint="#7d8592",
        accent="#1caae2", accent_text="#ffffff", accent_hover="#3fbde9", accent_pressed="#1690bd",
        link="#8ddcf0", selected="#1690bd", selected_text="#ffffff", hover="#4a4a50",
        header_bg="#4d4d54", header_text="#c4cad4", secondary_hover="#575860",
        disabled_bg="#5d5e66", disabled_text="#6b7280",
        ok_bg="#1e4030", ok_text="#b8e6cc", warn_bg="#453419", warn_text="#f0dba8",
        error_bg="#4a2323", error_text="#f2c6c6",
        json_key="#8ddcf0", json_string="#f0dba8", json_number="#c4b5fd", json_literal="#f9a8d4",
    ),
}
MONO = '"JetBrains Mono", "Cascadia Mono", "Consolas", monospace'   # réservé au contenu JSON
SANS = '"Segoe UI", "Helvetica Neue", Arial, sans-serif'


def console_stylesheet(t):
    css = f"""
#rmsConsole {{ background-color: {t['bg']}; }}
#rmsConsole QWidget {{ background-color: transparent; color: {t['text']}; font-family: {SANS}; font-size: 13px; }}
#rmsConsole QLabel {{ background-color: transparent; }}

#rmsHeader {{ background-color: {t['bg']}; border-bottom: 1px solid {t['border']}; }}
#rmsBadge {{ background-color: {t['accent']}; color: {t['accent_text']}; font-weight: 700;
             font-size: 13px; padding: 6px 10px; border-radius: 6px; }}
#rmsTitle {{ font-size: 22px; font-weight: 700; color: {t['text']}; }}
#rmsSubtitle {{ color: {t['muted']}; }}
#rmsStatus {{ padding: 6px 14px; border-radius: 10px; font-weight: 700;
              background-color: {t['header_bg']}; color: {t['muted']}; }}
#rmsStatus[state="ok"] {{ background-color: {t['ok_bg']}; color: {t['ok_text']}; }}
#rmsStatus[state="busy"] {{ background-color: {t['warn_bg']}; color: {t['warn_text']}; }}
#rmsStatus[state="error"] {{ background-color: {t['error_bg']}; color: {t['error_text']}; }}

#rmsSide {{ background-color: {t['panel']}; border-right: 1px solid {t['border']}; }}
#rmsCenter {{ background-color: {t['panel']}; }}
#rmsPreview {{ background-color: {t['panel']}; border-left: 1px solid {t['border']}; }}

#rmsSection {{ color: {t['text']}; font-size: 15px; font-weight: 700; }}
#rmsRule {{ background-color: {t['border']}; max-height: 1px; min-height: 1px; }}
#rmsFieldLabel {{ color: {t['muted']}; font-weight: 600; }}
#rmsNote {{ color: {t['muted']}; }}
#rmsConsole QLineEdit {{ background-color: {t['input']}; border: 1px solid {t['border_strong']}; border-radius: 5px;
                         padding: 8px; color: {t['text']}; selection-background-color: {t['accent']};
                         selection-color: {t['accent_text']}; }}
#rmsConsole QLineEdit:focus {{ border-color: {t['accent']}; }}
#rmsConsole QLineEdit:disabled {{ color: {t['faint']}; background-color: {t['bg']}; }}

#rmsPrimary {{ background-color: {t['accent']}; color: {t['accent_text']}; border: none; border-radius: 6px;
               padding: 9px 18px; font-weight: 600; }}
#rmsPrimary:hover {{ background-color: {t['accent_hover']}; }}
#rmsPrimary:pressed {{ background-color: {t['accent_pressed']}; }}
#rmsPrimary:disabled {{ background-color: {t['disabled_bg']}; color: {t['disabled_text']}; }}
#rmsConsole QPushButton#rmsSecondary, #rmsGhost {{ background-color: {t['panel']}; color: {t['text']};
               border: 1px solid {t['border_strong']}; border-radius: 6px; padding: 9px 18px; font-weight: 600; }}
#rmsConsole QPushButton#rmsSecondary:hover, #rmsGhost:hover {{ background-color: {t['secondary_hover']}; }}
#rmsConsole QPushButton#rmsSecondary:disabled, #rmsGhost:disabled {{ color: {t['disabled_text']};
               background-color: {t['bg']}; border-color: {t['border']}; }}
#rmsGhost:checked {{ border-color: {t['accent']}; color: {t['link']}; }}
#rmsClose, #rmsUp {{ background-color: {t['panel']}; border: 1px solid {t['border_strong']}; border-radius: 6px;
             color: {t['muted']}; font-size: 14px; font-weight: 600;
             min-width: 36px; max-width: 36px; min-height: 36px; max-height: 36px; padding: 0; }}
#rmsClose:hover, #rmsUp:hover {{ background-color: {t['secondary_hover']}; color: {t['text']}; }}
#rmsUp:disabled {{ color: {t['disabled_text']}; border-color: {t['border']}; }}

#rmsPermission {{ background-color: {t['warn_bg']}; border-radius: 10px; color: {t['warn_text']};
                  font-weight: 600; padding: 8px 12px; }}

#rmsCrumbBar {{ border-bottom: 1px solid {t['border']}; }}
#rmsCrumb {{ background-color: transparent; border: none; color: {t['link']}; font-weight: 600;
             font-size: 14px; padding: 4px 2px; }}
#rmsCrumb:hover {{ text-decoration: underline; }}
#rmsCrumbCurrent {{ color: {t['text']}; font-size: 14px; font-weight: 700; padding: 4px 2px; }}
#rmsCrumbSep {{ color: {t['faint']}; font-size: 14px; }}

#rmsConsole QTableView {{ background-color: {t['panel']}; border: none; outline: none;
                          selection-background-color: {t['selected']}; selection-color: {t['selected_text']}; }}
#rmsConsole QTableView::item {{ padding: 0 10px; border-bottom: 1px solid {t['border']}; }}
#rmsConsole QTableView::item:selected {{ background-color: {t['selected']}; color: {t['selected_text']}; }}
#rmsConsole QHeaderView::section {{ background-color: {t['header_bg']}; color: {t['header_text']}; border: none;
                                    border-right: 1px solid {t['border_strong']}; padding: 8px; font-weight: 600; }}
#rmsConsole QHeaderView::section:last {{ border-right: none; }}
#rmsListStatus {{ color: {t['muted']}; }}

#rmsKey {{ color: {t['link']}; font-weight: 600; font-size: 14px; }}
#rmsMeta {{ color: {t['muted']}; }}
#rmsSummary {{ color: {t['text']}; }}
#rmsPreviewBar {{ border-bottom: 1px solid {t['border']}; }}
#rmsConsole QPlainTextEdit {{ background-color: {t['panel_alt']}; border: none; font-family: {MONO};
                              font-size: 12px; color: {t['text']}; selection-background-color: {t['accent']};
                              selection-color: {t['accent_text']}; }}
#rmsEmpty {{ color: {t['muted']}; }}
#rmsEmptyTitle {{ color: {t['text']}; font-size: 15px; font-weight: 700; }}

#rmsConsole QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px 2px 2px 0; }}
#rmsConsole QScrollBar::handle:vertical {{ background: {t['border_strong']}; border-radius: 5px; min-height: 24px; }}
#rmsConsole QScrollBar::handle:vertical:pressed {{ background: {t['accent']}; }}
#rmsConsole QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0 2px 2px 2px; }}
#rmsConsole QScrollBar::handle:horizontal {{ background: {t['border_strong']}; border-radius: 5px; min-width: 24px; }}
#rmsConsole QScrollBar::handle:horizontal:pressed {{ background: {t['accent']}; }}
#rmsConsole QScrollBar::add-line, #rmsConsole QScrollBar::sub-line {{ width: 0; height: 0; }}
#rmsConsole QScrollBar::add-page, #rmsConsole QScrollBar::sub-page {{ background: none; }}
#rmsConsole QSplitter::handle {{ background-color: transparent; }}
#rmsConsole QSplitter::handle:hover {{ background-color: {t['accent']}; }}
"""
    # "#rmsX" seul est moins prioritaire que "#rmsConsole QWidget" : on préfixe
    # chaque règle par l'identifiant de la console pour qu'elle l'emporte.
    return re.sub(r"(^|,\s*)#rms(?!Console)", r"\1#rmsConsole #rms", css, flags=re.MULTILINE)


_ICON_SVG = {
    "folder": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c}" '
              'stroke-width="1.8" stroke-linejoin="round"><path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.3l2 2.2h8.7'
              'A1.5 1.5 0 0 1 21 8.7v9.8a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18.5z"/></svg>',
    "file": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{c}" '
            'stroke-width="1.8" stroke-linejoin="round"><path d="M6 3h8l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4'
            'a1 1 0 0 1 1-1z"/><path d="M14 3v4h4"/></svg>',
}


def _svg_icon(kind, color, size=18):
    renderer = QSvgRenderer(QByteArray(_ICON_SVG[kind].format(c=color).encode("utf-8")))
    pixmap = QPixmap(size * 2, size * 2)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class JsonHighlighter(QSyntaxHighlighter):
    """Coloration du JSON mis en forme : clés, chaînes, nombres, true/false/null."""

    _KEY = re.compile(r'"(?:[^"\\]|\\.)*"(?=\s*:)')
    _STRING = re.compile(r'"(?:[^"\\]|\\.)*"')
    _NUMBER = re.compile(r'(?<![\w.])-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b')
    _LITERAL = re.compile(r'\b(?:true|false|null)\b')

    def __init__(self, document, colors):
        super().__init__(document)
        self.set_colors(colors)

    def set_colors(self, t):
        def fmt(color):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            return f
        self._formats = {
            "key": fmt(t["json_key"]), "string": fmt(t["json_string"]),
            "number": fmt(t["json_number"]), "literal": fmt(t["json_literal"]),
        }
        self.rehighlight()

    def highlightBlock(self, text):
        keys = [(m.start(), m.end()) for m in self._KEY.finditer(text)]
        for start, end in keys:
            self.setFormat(start, end - start, self._formats["key"])
        strings = []
        for m in self._STRING.finditer(text):
            if (m.start(), m.end()) not in keys:
                strings.append((m.start(), m.end()))
                self.setFormat(m.start(), m.end() - m.start(), self._formats["string"])
        inside = keys + strings
        for name, pattern in (("number", self._NUMBER), ("literal", self._LITERAL)):
            for m in pattern.finditer(text):
                if not any(s <= m.start() < e for s, e in inside):
                    self.setFormat(m.start(), m.end() - m.start(), self._formats[name])


class HoverRowDelegate(QStyledItemDelegate):
    """Surligne toute la ligne survolée (le QSS « ::item:hover » ne colore qu'une cellule)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_row = -1
        self.color = QColor("#141e25")

    def paint(self, painter, option, index):
        if index.row() == self.hover_row and not (option.state & QStyle.StateFlag.State_Selected):
            painter.fillRect(option.rect, self.color)
        super().paint(painter, option, index)


# ------------------------------------------------------------ modèle de liste

class EntryModel(QAbstractTableModel):
    HEADERS = ("Nom", "Taille", "Modifié")
    KEY_ROLE = Qt.ItemDataRole.UserRole

    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._icons = {}

    def set_icons(self, folder_icon, file_icon):
        self._icons = {"folder": folder_icon, "file": file_icon}
        if self._entries:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._entries) - 1, 0))

    def clear(self):
        self.beginResetModel()
        self._entries = []
        self.endResetModel()

    def append(self, entries):
        if not entries:
            return
        start = len(self._entries)
        self.beginInsertRows(QModelIndex(), start, start + len(entries) - 1)
        self._entries.extend(entries)
        self.endInsertRows()

    def entry(self, row):
        return self._entries[row]

    def counts(self):
        folders = sum(1 for e in self._entries if e["is_dir"])
        return folders, len(self._entries) - folders

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._entries)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.HEADERS[section]
        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        e = self._entries[index.row()]
        column = index.column()
        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return e["name"] + ("/" if e["is_dir"] else "")
            if column == 1:
                return "—" if e["is_dir"] else rms.format_size(e["size"])
            if column == 2:
                return rms.format_date(e["modified"])
        elif role == Qt.ItemDataRole.DecorationRole and column == 0:
            return self._icons.get("folder" if e["is_dir"] else "file")
        elif role == Qt.ItemDataRole.TextAlignmentRole and column == 1:
            return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        elif role == Qt.ItemDataRole.ToolTipRole and column == 0:
            return e["key"] + ("\nDouble-clic pour ouvrir" if e["is_dir"] else "")
        elif role == self.KEY_ROLE:
            return e["key"]
        return None


class EntryFilter(QSortFilterProxyModel):
    """Filtre (insensible à la casse) sur le nom des entrées du dossier courant."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterKeyColumn(0)


# ----------------------------------------------------------------- threads

class ConnectWorker(QThread):
    connected = Signal(object, list, bool)   # client, entrées racine, racine devinée
    failed = Signal(str)

    def __init__(self, endpoint, access_key, secret_key, bucket, region, parent=None):
        super().__init__(parent)
        self.args = (endpoint, access_key, secret_key, bucket, region)

    def run(self):
        endpoint, access_key, secret_key, bucket, region = self.args
        try:
            client = rms.make_client(endpoint, access_key, secret_key, region)
            entries, probed = rms.list_root(client, bucket)
        except Exception as exc:
            self.failed.emit(rms.error_message(exc, endpoint))
            return
        self.connected.emit(client, entries, probed)


class ListWorker(QThread):
    batch = Signal(int, list)          # (numéro de requête, entrées)
    done = Signal(int, int)            # (numéro de requête, total)
    failed = Signal(int, str)

    def __init__(self, seq, client, bucket, prefix, endpoint, parent=None):
        super().__init__(parent)
        self.seq, self.client, self.bucket, self.prefix, self.endpoint = seq, client, bucket, prefix, endpoint
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            total = rms.list_folder(self.client, self.bucket, self.prefix,
                                    should_stop=lambda: self._stop,
                                    on_batch=lambda entries: self.batch.emit(self.seq, entries))
        except Exception as exc:
            if not self._stop:
                self.failed.emit(self.seq, rms.error_message(exc, self.endpoint))
            return
        if not self._stop:
            self.done.emit(self.seq, total)


class PreviewWorker(QThread):
    ready = Signal(int, bytes, str, str)   # (requête, brut, texte, résumé)
    failed = Signal(int, str)

    def __init__(self, seq, client, bucket, key, endpoint, parent=None):
        super().__init__(parent)
        self.seq, self.client, self.bucket, self.key, self.endpoint = seq, client, bucket, key, endpoint

    def run(self):
        try:
            raw = rms.fetch_object(self.client, self.bucket, self.key)
            text, parsed = rms.decode_payload(raw)
        except Exception as exc:
            self.failed.emit(self.seq, rms.error_message(exc, self.endpoint))
            return
        self.ready.emit(self.seq, raw, text, rms.payload_summary(parsed))


class DownloadWorker(QThread):
    """Téléchargement parallèle (voir rms_client.fast_download) : sélection ou dossier entier."""
    progress = Signal(dict)
    finished_ok = Signal(dict)
    failed = Signal(str)

    def __init__(self, client, bucket, output_dir, endpoint, base_prefix, keys=None, prefixes=None,
                 workers=32, zip_path=None, parent=None):
        super().__init__(parent)
        self.client, self.bucket, self.output_dir, self.endpoint = client, bucket, output_dir, endpoint
        self.options = dict(base_prefix=base_prefix, keys=keys, prefixes=prefixes, workers=workers,
                            zip_path=zip_path, skip_existing=True)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            stats = rms.fast_download(self.client, self.bucket, self.output_dir,
                                      should_stop=lambda: self._stop, on_progress=self.progress.emit,
                                      **self.options)
        except Exception as exc:
            self.failed.emit(str(exc) if isinstance(exc, RuntimeError) else rms.error_message(exc, self.endpoint))
            return
        stats["destination"] = self.options["zip_path"] or self.output_dir
        self.finished_ok.emit(stats)


# -------------------------------------------------------------------- onglet

class RmsConsoleTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rmsConsole")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._theme = THEMES["light"]
        self._client = None
        self._bucket = rms.DEFAULT_BUCKET
        self._endpoint_host = "api-rms.appesca.com"
        self._prefix = ""
        self._root_entries = []
        self._workers = set()
        self._list_seq = 0
        self._list_worker = None
        self._preview_seq = 0
        self._preview_key = None
        self._preview_raw = b""
        self._preview_text = ""
        self._root_probed = False
        self._build_ui()
        self.set_theme(False)  # clair par défaut, comme le reste de l'application
        self._set_status("idle")
        self._show_preview(False)
        self._update_empty_state()

    # ------------------------------------------------------------- interface

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)
        self.side = self._build_side()
        self.splitter.addWidget(self.side)
        self.splitter.addWidget(self._build_center())
        self.splitter.addWidget(self._build_preview())
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setSizes([330, 700, 560])
        root.addWidget(self.splitter, stretch=1)
        # le panneau d'aperçu n'apparaît que lorsqu'un fichier est sélectionné
        self.preview.setVisible(False)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("rmsHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(14)
        badge = QLabel("RMS")
        badge.setObjectName("rmsBadge")
        layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel("SALTEC · Console de stockage")
        title.setObjectName("rmsTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("rmsSubtitle")
        titles.addWidget(title)
        titles.addWidget(self.subtitle)
        layout.addLayout(titles, stretch=1)
        self.side_btn = QPushButton("Connexion")
        self.side_btn.setObjectName("rmsGhost")
        self.side_btn.setCheckable(True)
        self.side_btn.setChecked(True)
        self.side_btn.setToolTip("Afficher ou masquer le panneau de connexion")
        self.side_btn.toggled.connect(self._toggle_side)
        apply_pointer_cursor(self.side_btn)
        layout.addWidget(self.side_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.status = QLabel()
        self.status.setObjectName("rmsStatus")
        layout.addWidget(self.status, alignment=Qt.AlignmentFlag.AlignVCenter)
        return header

    def _toggle_side(self, visible):
        self.side.setVisible(visible)

    def _section_title(self, text):
        row = QHBoxLayout()
        row.setSpacing(12)
        label = QLabel(text)
        label.setObjectName("rmsSection")
        rule = QFrame()
        rule.setObjectName("rmsRule")
        row.addWidget(label)
        row.addWidget(rule, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)
        return row

    @staticmethod
    def _field(label_text, widget):
        box = QVBoxLayout()
        box.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("rmsFieldLabel")
        box.addWidget(label)
        box.addWidget(widget)
        return box

    def _build_side(self):
        side = QFrame()
        side.setObjectName("rmsSide")
        side.setMinimumWidth(300)
        side.setMaximumWidth(460)
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 24, 18, 18)
        layout.setSpacing(14)

        layout.addLayout(self._section_title("Connexion"))
        self.endpoint_edit = QLineEdit(rms.DEFAULT_ENDPOINT)
        layout.addLayout(self._field("Point de terminaison API", self.endpoint_edit))
        self.bucket_edit = QLineEdit(rms.DEFAULT_BUCKET)
        self.region_edit = QLineEdit(rms.DEFAULT_REGION)
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addLayout(self._field("Bucket", self.bucket_edit))
        row.addLayout(self._field("Région", self.region_edit))
        layout.addLayout(row)

        env_access, env_secret = rms.env_credentials()
        self.access_edit = QLineEdit(env_access)
        self.access_edit.setPlaceholderText("Access Key")
        self.secret_edit = QLineEdit(env_secret)
        self.secret_edit.setPlaceholderText("Secret Key")
        self.secret_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addLayout(self._field("Clé d'accès", self.access_edit))
        layout.addLayout(self._field("Clé secrète", self.secret_edit))
        for edit in (self.endpoint_edit, self.bucket_edit, self.region_edit, self.access_edit, self.secret_edit):
            edit.returnPressed.connect(self._on_connect_clicked)

        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.setObjectName("rmsPrimary")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        apply_pointer_cursor(self.connect_btn)
        layout.addWidget(self.connect_btn)

        note = QLabel("Les identifiants restent en mémoire de session uniquement — jamais enregistrés "
                      "ni transmis ailleurs qu'à votre point de terminaison.")
        if env_access:
            note.setText(note.text() + f"\nPré-remplis depuis les variables {rms.ENV_ACCESS_KEY} / {rms.ENV_SECRET_KEY}.")
        note.setObjectName("rmsNote")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addSpacing(12)
        layout.addLayout(self._section_title("Droits du compte"))
        self.permission = QLabel("Lecture seule — ListBucket · GetObject")
        self.permission.setObjectName("rmsPermission")
        self.permission.setWordWrap(True)
        layout.addWidget(self.permission)
        layout.addStretch(1)
        return side

    def _build_center(self):
        center = QFrame()
        center.setObjectName("rmsCenter")
        layout = QVBoxLayout(center)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        crumb_bar = QFrame()
        crumb_bar.setObjectName("rmsCrumbBar")
        crumb_layout = QHBoxLayout(crumb_bar)
        crumb_layout.setContentsMargins(16, 12, 16, 12)
        crumb_layout.setSpacing(10)
        self.up_btn = QPushButton("↑")
        self.up_btn.setObjectName("rmsUp")
        self.up_btn.setToolTip("Dossier parent (Retour arrière)")
        self.up_btn.clicked.connect(self._go_up)
        apply_pointer_cursor(self.up_btn)
        crumb_layout.addWidget(self.up_btn)
        self.crumbs = QHBoxLayout()
        self.crumbs.setSpacing(10)
        crumb_layout.addLayout(self.crumbs)
        crumb_layout.addStretch(1)
        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("rmsFilter")
        self.filter_edit.setPlaceholderText("Filtrer ce dossier…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.setFixedWidth(220)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        crumb_layout.addWidget(self.filter_edit)
        layout.addWidget(crumb_bar)

        self.model = EntryModel(self)
        self.proxy = EntryFilter(self)
        self.proxy.setSourceModel(self.model)
        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.table.setIconSize(QSize(16, 16))
        self.table.setMouseTracking(True)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.hover_delegate = HoverRowDelegate(self.table)
        self.table.setItemDelegate(self.hover_delegate)
        self.table.entered.connect(self._on_row_hovered)
        self.table.viewport().installEventFilter(self)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 90)
        header.resizeSection(2, 150)
        header.setHighlightSections(False)
        header.setMinimumSectionSize(60)
        self.table.viewport().setCursor(Qt.CursorShape.PointingHandCursor)
        # "activated" = double-clic ou Entrée selon la plateforme (un seul signal,
        # sinon le dossier serait ouvert deux fois)
        self.table.activated.connect(self._on_entry_activated)
        self.table.selectionModel().currentRowChanged.connect(self._on_current_changed)
        self.table.selectionModel().selectionChanged.connect(lambda *_: self._update_download_button())
        layout.addWidget(self.table, stretch=1)

        # état vide (avant connexion / dossier vide) à la place du tableau
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.addStretch(1)
        self.empty_title = QLabel("Non connecté")
        self.empty_title.setObjectName("rmsEmptyTitle")
        self.empty_text = QLabel("Renseignez vos clés à gauche puis cliquez sur « Se connecter ».")
        self.empty_text.setObjectName("rmsEmpty")
        self.empty_text.setWordWrap(True)
        for label in (self.empty_title, self.empty_text):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(label)
        empty_layout.addStretch(2)
        layout.addWidget(self.empty_state, stretch=1)

        QShortcut(QKeySequence(Qt.Key.Key_Backspace), self.table, activated=self._go_up)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=lambda: self._show_preview(False))

        footer = QHBoxLayout()
        footer.setContentsMargins(16, 10, 16, 12)
        self.list_status = QLabel("Connectez-vous pour parcourir le bucket.")
        self.list_status.setObjectName("rmsListStatus")
        footer.addWidget(self.list_status, stretch=1)
        self.download_btn = QPushButton("↓ Télécharger la sélection")
        self.download_btn.setObjectName("rmsSecondary")
        self.download_btn.clicked.connect(self._download_selection)
        apply_pointer_cursor(self.download_btn)
        set_button_enabled(self.download_btn, False)
        footer.addWidget(self.download_btn)
        self.folder_btn = QPushButton("↓ Télécharger ce dossier")
        self.folder_btn.setObjectName("rmsSecondary")
        self.folder_btn.setToolTip("Tout le contenu du dossier affiché, sous-dossiers compris, "
                                   "sans avoir à sélectionner les fichiers")
        self.folder_btn.clicked.connect(self._download_folder)
        apply_pointer_cursor(self.folder_btn)
        set_button_enabled(self.folder_btn, False)
        footer.addWidget(self.folder_btn)
        layout.addLayout(footer)

        options = QHBoxLayout()
        options.setContentsMargins(16, 0, 16, 12)
        options.setSpacing(10)
        threads_label = QLabel("Téléchargements simultanés")
        threads_label.setObjectName("rmsNote")
        options.addWidget(threads_label)
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, rms.DOWNLOAD_MAX_WORKERS)
        self.threads_spin.setValue(32)
        self.threads_spin.setToolTip("Nombre de fichiers téléchargés en même temps. 32 convient en général ; "
                                     "baissez si le serveur renvoie des erreurs.")
        options.addWidget(self.threads_spin)
        self.zip_check = QCheckBox("Une seule archive ZIP (plus rapide sous Windows)")
        self.zip_check.setToolTip("Écrire des centaines de milliers de petits fichiers est lent sous Windows "
                                  "(antivirus, système de fichiers). Une archive ZIP évite ce coût.")
        options.addWidget(self.zip_check)
        options.addStretch(1)
        self.download_progress = QProgressBar()
        self.download_progress.setFixedWidth(220)
        self.download_progress.setVisible(False)
        options.addWidget(self.download_progress)
        self.stop_download_btn = QPushButton("Arrêter")
        self.stop_download_btn.setObjectName("rmsSecondary")
        self.stop_download_btn.clicked.connect(self._stop_download)
        apply_pointer_cursor(self.stop_download_btn)
        self.stop_download_btn.setVisible(False)
        options.addWidget(self.stop_download_btn)
        layout.addLayout(options)
        self._download_worker = None
        self._render_breadcrumb()
        return center

    def _build_preview(self):
        self.preview = QFrame()
        self.preview.setObjectName("rmsPreview")
        layout = QVBoxLayout(self.preview)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        top = QFrame()
        top.setObjectName("rmsPreviewBar")
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(24, 18, 18, 16)
        top_layout.setSpacing(6)
        title_row = QHBoxLayout()
        self.preview_key = QLabel()
        self.preview_key.setObjectName("rmsKey")
        self.preview_key.setWordWrap(True)
        self.preview_key.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title_row.addWidget(self.preview_key, stretch=1)
        close_btn = QPushButton("✕")
        close_btn.setObjectName("rmsClose")
        close_btn.setToolTip("Fermer l'aperçu (Échap)")
        close_btn.clicked.connect(lambda: self._show_preview(False))
        apply_pointer_cursor(close_btn)
        title_row.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)
        top_layout.addLayout(title_row)
        self.preview_meta = QLabel()
        self.preview_meta.setObjectName("rmsMeta")
        top_layout.addWidget(self.preview_meta)
        self.preview_summary = QLabel()
        self.preview_summary.setObjectName("rmsSummary")
        self.preview_summary.setWordWrap(True)
        top_layout.addWidget(self.preview_summary)
        layout.addWidget(top)

        actions = QFrame()
        actions.setObjectName("rmsPreviewBar")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(24, 12, 18, 12)
        actions_layout.setSpacing(10)
        self.save_gz_btn = QPushButton("↓ Fichier .gz d'origine")
        self.save_json_btn = QPushButton("↓ JSON décompressé")
        for button, slot in ((self.save_gz_btn, self._save_original), (self.save_json_btn, self._save_json)):
            button.setObjectName("rmsSecondary")
            button.clicked.connect(slot)
            apply_pointer_cursor(button)
            actions_layout.addWidget(button)
        actions_layout.addStretch(1)
        self.copy_btn = QPushButton("Copier le chemin")
        self.copy_btn.setObjectName("rmsGhost")
        self.copy_btn.clicked.connect(self._copy_key)
        apply_pointer_cursor(self.copy_btn)
        actions_layout.addWidget(self.copy_btn)
        layout.addWidget(actions)

        self.json_view = QPlainTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.json_view.document().setDocumentMargin(18)
        mono = QFont()
        mono.setFamilies(["JetBrains Mono", "Cascadia Mono", "Consolas", "Courier New"])
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.json_view.setFont(mono)
        self.highlighter = JsonHighlighter(self.json_view.document(), self._theme)
        layout.addWidget(self.json_view, stretch=1)

        self.preview_empty = QLabel("Sélectionnez un fichier pour afficher son contenu.")
        self.preview_empty.setObjectName("rmsEmpty")
        self.preview_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.preview_empty, stretch=1)
        return self.preview

    # ------------------------------------------------------------------ thème

    def set_theme(self, is_dark):
        self._theme = THEMES["dark" if is_dark else "light"]
        self.setStyleSheet(console_stylesheet(self._theme))
        self.model.set_icons(_svg_icon("folder", self._theme["accent"]), _svg_icon("file", self._theme["muted"]))
        self.highlighter.set_colors(self._theme)
        self.hover_delegate.color = QColor(self._theme["hover"])
        self.table.viewport().update()
        self._render_breadcrumb()

    def _set_status(self, state, text=None):
        labels = {
            "idle": "Déconnecté",
            "busy": "Connexion…",
            "ok": f"Connecté · {self._bucket}",
            "error": "Échec de connexion",
        }
        self.status.setText(text or labels[state])
        self.status.setToolTip(self._endpoint_host if state == "ok" else "")
        self.status.setProperty("state", state)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        self.subtitle.setText(f"MinIO / S3  ·  {self._endpoint_host}")

    # ------------------------------------------------------------- connexion

    def _start(self, worker):
        """Garde une référence au thread jusqu'à sa fin (sinon Qt le détruit en cours d'exécution)."""
        self._workers.add(worker)
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_connect_clicked(self):
        if self._client is not None and self.sender() is self.connect_btn:
            self._disconnect()
            return
        access, secret = self.access_edit.text().strip(), self.secret_edit.text().strip()
        if not access or not secret:
            QMessageBox.warning(self.window(), "Connexion", "Renseignez la clé d'accès et la clé secrète.")
            return
        try:
            self._endpoint_host, _secure = rms.normalize_endpoint(self.endpoint_edit.text())
        except ValueError as exc:
            QMessageBox.warning(self.window(), "Connexion", str(exc))
            return
        self._bucket = self.bucket_edit.text().strip() or rms.DEFAULT_BUCKET
        self._set_status("busy")
        set_button_busy(self.connect_btn, True)
        set_button_enabled(self.connect_btn, False)
        worker = ConnectWorker(self.endpoint_edit.text(), access, secret, self._bucket,
                               self.region_edit.text().strip(), parent=self)
        worker.connected.connect(self._on_connected)
        worker.failed.connect(self._on_connect_failed)
        self._start(worker)

    def _on_connected(self, client, entries, probed):
        self._client = client
        self._root_entries = entries
        set_button_busy(self.connect_btn, False)
        set_button_enabled(self.connect_btn, True)
        self.connect_btn.setText("Se déconnecter")
        for edit in (self.endpoint_edit, self.bucket_edit, self.region_edit, self.access_edit, self.secret_edit):
            edit.setEnabled(False)
        self._set_status("ok")
        self._root_probed = probed
        # plus de place pour la navigation : le panneau se rouvre avec le bouton « Connexion »
        self.side_btn.setChecked(False)
        self._open_prefix("")

    def _on_connect_failed(self, message):
        set_button_busy(self.connect_btn, False)
        set_button_enabled(self.connect_btn, True)
        self._set_status("error")
        self.side_btn.setChecked(True)
        QMessageBox.critical(self.window(), "Connexion RMS", message)

    def _disconnect(self):
        if self._list_worker is not None:
            self._list_worker.stop()
        self._client = None
        self._list_seq += 1
        self._preview_seq += 1
        self.model.clear()
        self._prefix = ""
        self._render_breadcrumb()
        self._show_preview(False)
        self.connect_btn.setText("Se connecter")
        for edit in (self.endpoint_edit, self.bucket_edit, self.region_edit, self.access_edit, self.secret_edit):
            edit.setEnabled(True)
        self.list_status.setText("Connectez-vous pour parcourir le bucket.")
        self.side_btn.setChecked(True)
        self._set_status("idle")
        self._update_empty_state()
        self._update_download_button()

    # ------------------------------------------------------------ navigation

    def _render_breadcrumb(self):
        while self.crumbs.count():
            item = self.crumbs.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        parts = [p for p in self._prefix.split("/") if p]
        segments = [(self._bucket, "")] + [(p, "/".join(parts[:i + 1]) + "/") for i, p in enumerate(parts)]
        for i, (label, prefix) in enumerate(segments):
            if i:
                sep = QLabel("/")
                sep.setObjectName("rmsCrumbSep")
                self.crumbs.addWidget(sep)
            if i == len(segments) - 1:
                current = QLabel(label)
                current.setObjectName("rmsCrumbCurrent")
                self.crumbs.addWidget(current)
            else:
                button = QPushButton(label)
                button.setObjectName("rmsCrumb")
                button.setFlat(True)
                button.clicked.connect(lambda _checked=False, p=prefix: self._open_prefix(p))
                apply_pointer_cursor(button)
                self.crumbs.addWidget(button)

    def _go_up(self):
        if self._client is None or not self._prefix:
            return
        parts = [p for p in self._prefix.split("/") if p][:-1]
        self._open_prefix("/".join(parts) + "/" if parts else "")

    def _update_empty_state(self, loading=False):
        connected = self._client is not None
        has_rows = self.model.rowCount() > 0
        show_table = connected and (has_rows or loading)
        self.table.setVisible(show_table)
        self.empty_state.setVisible(not show_table)
        if not connected:
            self.empty_title.setText("Non connecté")
            self.empty_text.setText("Renseignez vos clés dans le panneau « Connexion » puis cliquez sur « Se connecter ».")
        else:
            self.empty_title.setText("Dossier vide")
            self.empty_text.setText("Aucun fichier à cet emplacement. Utilisez ↑ pour revenir au dossier parent.")
        self.up_btn.setEnabled(connected and bool(self._prefix))

    def _on_row_hovered(self, index):
        row = index.row() if index.isValid() else -1
        if row != self.hover_delegate.hover_row:
            self.hover_delegate.hover_row = row
            self.table.viewport().update()

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Type.Leave:
            self.hover_delegate.hover_row = -1
            self.table.viewport().update()
        return super().eventFilter(obj, event)

    def _open_prefix(self, prefix):
        if self._client is None:
            return
        if self._list_worker is not None:
            self._list_worker.stop()
            self._list_worker = None
        self._list_seq += 1
        self._prefix = prefix
        self.filter_edit.blockSignals(True)
        self.filter_edit.clear()
        self.filter_edit.blockSignals(False)
        self.proxy.setFilterFixedString("")
        self.model.clear()
        self._render_breadcrumb()
        self._update_download_button()

        self.hover_delegate.hover_row = -1
        if prefix == "":
            self.model.append(self._root_entries)
            note = " (racine non listable : dossiers pays détectés)" if self._root_probed else ""
            self._update_list_status(done=True, note=note)
            self._update_empty_state()
            return

        self.list_status.setText("Chargement…")
        self._update_empty_state(loading=True)
        worker = ListWorker(self._list_seq, self._client, self._bucket, prefix, self._endpoint_host, parent=self)
        worker.batch.connect(self._on_list_batch)
        worker.done.connect(self._on_list_done)
        worker.failed.connect(self._on_list_failed)
        self._list_worker = worker
        self._start(worker)

    def _on_list_batch(self, seq, entries):
        if seq != self._list_seq:
            return
        self.model.append(entries)
        self._update_list_status(done=False)

    def _on_list_done(self, seq, _total):
        if seq != self._list_seq:
            return
        self._list_worker = None
        self._update_list_status(done=True)
        self._update_empty_state()

    def _on_list_failed(self, seq, message):
        if seq != self._list_seq:
            return
        self._list_worker = None
        self.list_status.setText("Échec du listage.")
        self._update_empty_state()
        QMessageBox.warning(self.window(), "Listage RMS", message)

    def _update_list_status(self, done, note=""):
        folders, files = self.model.counts()
        parts = []
        if folders:
            parts.append(f"{folders} dossier{'s' if folders > 1 else ''}")
        if files:
            parts.append(f"{files:,} fichier{'s' if files > 1 else ''}".replace(",", " "))
        text = " · ".join(parts) or "Dossier vide"
        shown = self.proxy.rowCount()
        if self.filter_edit.text() and shown != folders + files:
            text = f"{shown} affiché(s) sur {folders + files} · " + text
        self.list_status.setText(text + note if done else f"Chargement… {text}")

    def _on_filter_changed(self, text):
        self.proxy.setFilterFixedString(text.strip())
        self._update_list_status(done=self._list_worker is None)

    def _entry_at(self, proxy_index):
        if not proxy_index.isValid():
            return None
        row = self.proxy.mapToSource(proxy_index).row()
        return self.model.entry(row) if 0 <= row < self.model.rowCount() else None

    def _on_entry_activated(self, proxy_index):
        entry = self._entry_at(proxy_index)
        if entry is not None and entry["is_dir"]:
            self._open_prefix(entry["key"])

    def _on_current_changed(self, current, _previous):
        entry = self._entry_at(current)
        if entry is None or entry["is_dir"]:
            self._preview_seq += 1
            self._show_preview(False)
            return
        self._load_preview(entry)

    # --------------------------------------------------------------- aperçu

    def _show_preview(self, visible, loading=False):
        if visible and not self.preview.isVisible():
            self.preview.setVisible(True)
            total = sum(self.splitter.sizes())
            side = self.splitter.sizes()[0] if self.side.isVisible() else 0
            rest = max(400, total - side)
            self.splitter.setSizes([side, rest // 2, rest - rest // 2])
        elif not visible:
            self.preview.setVisible(False)
        self.json_view.setVisible(visible and not loading)
        self.preview_empty.setVisible(not visible or loading)
        if loading:
            self.preview_empty.setText("Chargement de l'aperçu…")
        elif not visible:
            self.preview_empty.setText("Sélectionnez un fichier pour afficher son contenu.")
            self.preview_key.setText("Aperçu")
            self.preview_meta.clear()
            self.preview_summary.clear()
            self._preview_key = None
        for button in (self.save_gz_btn, self.save_json_btn):
            set_button_enabled(button, visible and not loading)
        set_button_enabled(self.copy_btn, visible and bool(self._preview_key))

    def _load_preview(self, entry):
        if self._client is None or entry["key"] == self._preview_key:
            return
        self._preview_seq += 1
        self._preview_key = entry["key"]
        self.preview_key.setText(entry["key"])
        self.preview_meta.setText(rms.format_size(entry["size"]))
        self.preview_summary.clear()
        if entry["size"] and entry["size"] > rms.PREVIEW_MAX_BYTES:
            self._show_preview(True, loading=True)
            self.preview_empty.setText("Fichier trop volumineux pour l'aperçu : utilisez « Télécharger la sélection ».")
            return
        self._show_preview(True, loading=True)
        worker = PreviewWorker(self._preview_seq, self._client, self._bucket, entry["key"],
                               self._endpoint_host, parent=self)
        worker.ready.connect(self._on_preview_ready)
        worker.failed.connect(self._on_preview_failed)
        self._start(worker)

    def _on_preview_ready(self, seq, raw, text, summary):
        if seq != self._preview_seq:
            return  # l'utilisateur a déjà sélectionné un autre fichier
        self._preview_raw, self._preview_text = raw, text
        self.preview_meta.setText(f"{rms.format_size(len(raw))}  ·  récupéré {datetime.now():%H:%M:%S}")
        self.preview_summary.setText(summary)
        self.json_view.setPlainText(text)
        self._show_preview(True)

    def _on_preview_failed(self, seq, message):
        if seq != self._preview_seq:
            return
        self._preview_key = None
        self._show_preview(True, loading=True)
        self.preview_empty.setText(message)

    def _copy_key(self):
        if self._preview_key:
            QGuiApplication.clipboard().setText(self._preview_key)
            self.copy_btn.setText("Copié ✓")
            QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copier le chemin"))

    def _default_name(self, suffix):
        name = rms.entry_name(self._preview_key or "fichier", self._prefix) or "fichier"
        name = name.split("/")[-1]
        return name if suffix == ".gz" else re.sub(r"\.gz$", "", name)

    def _save_original(self):
        if not self._preview_raw:
            return
        path, _ = QFileDialog.getSaveFileName(self.window(), "Enregistrer le fichier d'origine", self._default_name(".gz"),
                                              "Fichier compressé (*.gz);;Tous les fichiers (*)")
        if path:
            self._write(path, self._preview_raw)

    def _save_json(self):
        if not self._preview_text:
            return
        path, _ = QFileDialog.getSaveFileName(self.window(), "Enregistrer le JSON décompressé", self._default_name(".json"),
                                              "JSON (*.json);;Tous les fichiers (*)")
        if path:
            self._write(path, self._preview_text.encode("utf-8"))

    def _write(self, path, data):
        try:
            Path(path).write_bytes(data)
        except OSError as exc:
            QMessageBox.warning(self.window(), "Enregistrement", f"Impossible d'écrire le fichier :\n{exc}")

    # -------------------------------------------------------- téléchargement

    def _selected_files(self):
        keys = []
        for index in self.table.selectionModel().selectedRows():
            entry = self._entry_at(index)
            if entry is not None and not entry["is_dir"]:
                keys.append(entry["key"])
        return keys

    def _update_download_button(self):
        busy = getattr(self, "_download_worker", None) is not None
        keys = self._selected_files() if self._client is not None else []
        self.download_btn.setText(f"↓ Télécharger la sélection ({len(keys)})" if keys else "↓ Télécharger la sélection")
        set_button_enabled(self.download_btn, bool(keys) and not busy)
        if hasattr(self, "folder_btn"):
            set_button_enabled(self.folder_btn, self._client is not None and bool(self._prefix) and not busy)

    def _download_selection(self):
        keys = self._selected_files()
        if keys and self._client is not None:
            self._start_download(keys=keys, label=f"{len(keys)} fichier(s) sélectionné(s)")

    def _download_folder(self):
        if self._client is None or not self._prefix:
            return
        depth = len([p for p in self._prefix.split("/") if p])
        if depth < 4:   # pays / année / mois : potentiellement des centaines de milliers de fichiers
            answer = QMessageBox.question(
                self.window(), "Téléchargement volumineux",
                f"« {self._prefix} » peut contenir des centaines de milliers de fichiers.\n"
                "Le téléchargement peut durer longtemps. Continuer ?")
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._start_download(prefixes=[self._prefix], label=f"dossier {self._prefix}")

    def _start_download(self, label, keys=None, prefixes=None):
        zip_path = None
        if self.zip_check.isChecked():
            default = (self._prefix.strip("/").replace("/", "_") or self._bucket) + ".zip"
            zip_path, _ = QFileDialog.getSaveFileName(self.window(), "Enregistrer l'archive ZIP", default, "ZIP (*.zip)")
            if not zip_path:
                return
            output_dir = os.path.dirname(zip_path)
        else:
            output_dir = QFileDialog.getExistingDirectory(self.window(), "Choisir le dossier de téléchargement")
            if not output_dir:
                return
        self._download_label = label
        worker = DownloadWorker(self._client, self._bucket, output_dir, self._endpoint_host, self._prefix,
                                keys=keys, prefixes=prefixes, workers=self.threads_spin.value(),
                                zip_path=zip_path, parent=self)
        worker.progress.connect(self._on_download_progress)
        worker.finished_ok.connect(self._on_download_done)
        worker.failed.connect(self._on_download_failed)
        self._download_worker = worker
        self.download_progress.setRange(0, len(keys) if keys else 0)   # dossier : total inconnu au départ
        self.download_progress.setValue(0)
        self.download_progress.setVisible(True)
        self.stop_download_btn.setVisible(True)
        set_button_enabled(self.stop_download_btn, True)
        self.threads_spin.setEnabled(False)
        self.zip_check.setEnabled(False)
        self.list_status.setText(f"Téléchargement de {label}…")
        self._update_download_button()
        self._start(worker)

    @staticmethod
    def _download_text(s):
        done = s["telecharges"] + s["deja_presents"]
        rate = done / max(s.get("duree", 0), 0.1)
        listed = f"{s['listes']:,}" + ("" if s["listage_termine"] else "+")
        parts = [f"{done:,} / {listed} fichiers", f"{rate:.0f} fichiers/s", rms.format_size(s["octets"])]
        if s["deja_presents"]:
            parts.append(f"{s['deja_presents']:,} déjà présents")
        if s["erreurs"]:
            parts.append(f"{s['erreurs']:,} erreur(s)")
        if s["listage_termine"] and rate > 0:
            remaining = (s["listes"] - done - s["erreurs"]) / rate
            if remaining > 1:
                parts.append(f"reste ~{int(remaining // 60)} min {int(remaining % 60):02d} s")
        return " · ".join(parts).replace(",", " ")

    def _on_download_progress(self, s):
        done = s["telecharges"] + s["deja_presents"] + s["erreurs"]
        if s["listage_termine"] or self.download_progress.maximum() > 0:
            self.download_progress.setRange(0, max(s["listes"], self.download_progress.maximum(), 1))
            self.download_progress.setValue(done)
        self.list_status.setText(f"Téléchargement… {self._download_text(s)}")

    def _stop_download(self):
        if self._download_worker is not None:
            self._download_worker.stop()
            set_button_enabled(self.stop_download_btn, False)
            self.list_status.setText("Arrêt en cours (fin des téléchargements en cours)…")

    def _end_download(self):
        self._download_worker = None
        self.download_progress.setVisible(False)
        self.stop_download_btn.setVisible(False)
        self.threads_spin.setEnabled(True)
        self.zip_check.setEnabled(True)
        self._update_download_button()
        self._update_list_status(done=True)

    def _on_download_done(self, s):
        self._end_download()
        state = "arrêté" if s.get("arrete") else "terminé"
        message = (f"Téléchargement {state} ({self._download_label}).\n\n{self._download_text(s)}\n\n"
                   f"Enregistré dans :\n{s['destination']}")
        if s.get("derniere_erreur"):
            message += f"\n\nDernière erreur : {s['derniere_erreur']}"
        if s.get("arrete") and not self.zip_check.isChecked():
            message += "\n\nRelancez le même téléchargement pour reprendre : les fichiers déjà présents sont sautés."
        QMessageBox.information(self.window(), "Téléchargement", message)

    def _on_download_failed(self, message):
        self._end_download()
        QMessageBox.warning(self.window(), "Téléchargement", message)

    def closeEvent(self, event):
        if self._list_worker is not None:
            self._list_worker.stop()
        if self._download_worker is not None:
            self._download_worker.stop()
        super().closeEvent(event)