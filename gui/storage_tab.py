import gzip
import os
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from gui.rms_client import describe_http_error as _describe
from gui.cursor_utils import apply_pointer_cursor, set_button_busy, set_button_enabled

S3_ENDPOINT = "api-rms.appesca.com"
S3_BUCKET = "rms-saltec"


class StorageWorker(QThread):
    object_found = Signal(dict)
    progress = Signal(int, int)
    finished_ok = Signal(str)
    failed = Signal(str)
    preview_ready = Signal(str)

    def __init__(self, mode, endpoint, access_key, secret_key, bucket, prefix, region="us-east-1", output_dir="", object_names=None, object_name="", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.prefix = prefix
        self.region = region
        self.output_dir = output_dir
        self.object_names = object_names or []
        self.object_name = object_name

    def run(self):
        try:
            from minio import Minio
            from minio.error import S3Error

            client = Minio(
                self.endpoint.removeprefix("https://").removeprefix("http://").rstrip("/"),
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=True,
                region=self.region or None,
            )
            if self.mode == "list":
                self._list_objects(client)
            elif self.mode == "preview":
                self._preview_object(client)
            else:
                self._download_objects(client)
        except S3Error as exc:
            messages = {
                "InvalidAccessKeyId": "Access Key invalide ou inconnue.",
                "SignatureDoesNotMatch": "Secret Key incorrecte ou signature invalide.",
                "AccessDenied": "Accès refusé : vérifiez les droits ListBucket/GetObject.",
                "NoSuchBucket": "Le bucket demandé n’existe pas ou n’est pas accessible.",
            }
            detail = messages.get(exc.code, str(exc))
            self.failed.emit(f"Erreur API S3 ({exc.code}) : {detail}")
        except Exception as exc:
            message = _describe(exc, S3_ENDPOINT)
            if message is None:
                message = f"Erreur API S3 : {type(exc).__name__}: {exc}"
            self.failed.emit(message)

    def _list_objects(self, client):
        objects = client.list_objects(self.bucket, prefix=self.prefix, recursive=True)
        for item in objects:
            name = str(item.object_name)
            if not name.casefold().endswith(".json.gz"):
                continue
            self.object_found.emit({
                "name": name,
                "size": int(item.size or 0),
                "last_modified": item.last_modified.isoformat(sep=" ", timespec="seconds")
                if item.last_modified else "",
            })
        self.finished_ok.emit("Liste chargée")

    def _download_objects(self, client):
        total = len(self.object_names)
        downloaded = 0
        output_root = Path(self.output_dir).resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        for object_name in self.object_names:
            relative_name = Path(object_name.replace("/", os.sep))
            if relative_name.is_absolute() or ".." in relative_name.parts:
                raise ValueError(f"Nom d'objet invalide : {object_name}")
            destination = (output_root / relative_name).resolve()
            if output_root not in destination.parents:
                raise ValueError(f"Chemin de téléchargement invalide : {object_name}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            response = client.get_object(self.bucket, object_name)
            try:
                with destination.open("wb") as file:
                    for chunk in response.stream(1024 * 1024):
                        file.write(chunk)
            finally:
                response.close()
                response.release_conn()
            downloaded += 1
            self.progress.emit(downloaded, total)
        self.finished_ok.emit(f"{downloaded} fichier(s) téléchargé(s)")

    def _preview_object(self, client):
        response = client.get_object(self.bucket, self.object_name)
        try:
            content = response.read()
        finally:
            response.close()
            response.release_conn()
        try:
            text = gzip.decompress(content).decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"Impossible de décompresser l'objet JSON : {exc}") from exc
        self.preview_ready.emit(text)
        self.finished_ok.emit("Aperçu chargé")


class StorageExtractionTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._pending_preview = False
        self._previewed_name = None
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        title = QLabel("Extraction API RMS SALTEC")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        subtitle = QLabel("Listez et téléchargez les fichiers JSON compressés depuis le stockage S3.")
        subtitle.setObjectName("mutedLabel")
        root.addWidget(subtitle)

        connection_box = QGroupBox("Connexion S3")
        form = QFormLayout(connection_box)
        form.setContentsMargins(16, 18, 16, 16)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)
        self.access_key_edit = QLineEdit()
        self.access_key_edit.setPlaceholderText("Access Key")
        self.secret_key_edit = QLineEdit()
        self.secret_key_edit.setPlaceholderText("Secret Key")
        self.secret_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.region_edit = QLineEdit("us-east-1")
        self.prefix_edit = QLineEdit()
        self.prefix_edit.setPlaceholderText("Exemple : MG/2026/10/")
        form.addRow("Access Key", self.access_key_edit)
        form.addRow("Secret Key", self.secret_key_edit)
        form.addRow("Région", self.region_edit)
        form.addRow("Préfixe", self.prefix_edit)
        root.addWidget(connection_box)

        actions = QHBoxLayout()
        self.list_btn = QPushButton("Se connecter")
        self.list_btn.clicked.connect(self.list_objects)
        apply_pointer_cursor(self.list_btn)
        self.download_btn = QPushButton("Télécharger la sélection")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.download_selected)
        apply_pointer_cursor(self.download_btn)
        self.output_edit = QLineEdit(str(Path("data") / "api_downloads"))
        self.output_btn = QPushButton("Dossier…")
        self.output_btn.clicked.connect(self.choose_output_dir)
        apply_pointer_cursor(self.output_btn)
        actions.addWidget(self.list_btn)
        actions.addWidget(self.download_btn)
        actions.addWidget(self.output_edit, stretch=1)
        actions.addWidget(self.output_btn)
        root.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        root.addWidget(self.progress)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Objet", "Taille (octets)", "Dernière modification"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._selection_changed)

        preview_panel = QWidget()
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(0, 8, 0, 0)
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("Aperçu JSON décompressé"))
        self.download_json_btn = QPushButton("Télécharger le JSON")
        self.download_json_btn.setEnabled(False)
        self.download_json_btn.clicked.connect(self.download_preview)
        apply_pointer_cursor(self.download_json_btn)
        preview_header.addWidget(self.download_json_btn)
        preview_layout.addLayout(preview_header)
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText("Sélectionnez un fichier .json.gz pour afficher son contenu.")
        preview_layout.addWidget(self.preview_edit)

        data_splitter = QSplitter(Qt.Orientation.Vertical)
        data_splitter.addWidget(self.table)
        data_splitter.addWidget(preview_panel)
        data_splitter.setStretchFactor(0, 3)
        data_splitter.setStretchFactor(1, 2)
        root.addWidget(data_splitter, stretch=1)

        self.status_label = QLabel("Prêt")
        self.status_label.setObjectName("mutedLabel")
        root.addWidget(self.status_label)

    def _credentials(self):
        access_key = self.access_key_edit.text().strip()
        secret_key = self.secret_key_edit.text().strip()
        region = self.region_edit.text().strip()
        if not all((access_key, secret_key, region)):
            QMessageBox.warning(self, "Informations manquantes", "Renseignez les clés d'accès et la région.")
            return None
        return S3_ENDPOINT, access_key, secret_key, S3_BUCKET, region

    def list_objects(self):
        credentials = self._credentials()
        if credentials is None:
            return
        self.table.setRowCount(0)
        self._set_busy(True, "Liste en cours…")
        endpoint, access_key, secret_key, bucket, region = credentials
        self.worker = StorageWorker(
            "list", endpoint, access_key, secret_key, bucket, self.prefix_edit.text().strip(), region, parent=self
        )
        self.worker.object_found.connect(self._add_object)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._after_worker)
        self.worker.start()

    def download_selected(self):
        credentials = self._credentials()
        selected_rows = self.table.selectionModel().selectedRows()
        if credentials is None or not selected_rows:
            return
        object_names = [
            self.table.item(index.row(), 0).data(Qt.ItemDataRole.UserRole)
            for index in selected_rows
        ]
        self._set_busy(True, "Téléchargement en cours…")
        self.progress.setMaximum(len(object_names))
        self.progress.setValue(0)
        self.progress.setVisible(True)
        endpoint, access_key, secret_key, bucket, region = credentials
        self.worker = StorageWorker(
            "download", endpoint, access_key, secret_key, bucket,
            self.prefix_edit.text().strip(), region, self.output_edit.text().strip(), object_names, parent=self,
        )
        self.worker.progress.connect(lambda done, total: self.progress.setValue(done))
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._after_worker)
        self.worker.start()

    def _add_object(self, item):
        row = self.table.rowCount()
        self.table.insertRow(row)
        name_item = QTableWidgetItem(item["name"])
        name_item.setData(Qt.ItemDataRole.UserRole, item["name"])
        self.table.setItem(row, 0, name_item)
        self.table.setItem(row, 1, QTableWidgetItem(str(item["size"])))
        self.table.setItem(row, 2, QTableWidgetItem(item["last_modified"]))

    def _update_download_state(self):
        has_selection = bool(self.table.selectionModel().selectedRows())
        set_button_enabled(self.download_btn, has_selection)
        set_button_enabled(self.download_json_btn, has_selection)

    def _worker_running(self):
        return self.worker is not None and self.worker.isRunning()

    def _selection_changed(self):
        self._update_download_state()
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            self.preview_edit.clear()
            self._previewed_name = None
            return
        if self._worker_running():
            # une liste, un téléchargement ou un autre aperçu est en cours : on
            # attend sa fin (voir _after_worker) au lieu d'en lancer un second
            self._pending_preview = True
            return
        object_name = self.table.item(selected_rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if object_name == self._previewed_name:
            return
        credentials = self._credentials()
        if credentials is None:
            return
        endpoint, access_key, secret_key, bucket, region = credentials
        self._previewed_name = object_name
        self.preview_edit.setPlainText("Chargement de l'aperçu…")
        self.worker = StorageWorker(
            "preview", endpoint, access_key, secret_key, bucket,
            self.prefix_edit.text().strip(), region, object_name=object_name, parent=self,
        )
        self.worker.preview_ready.connect(self.preview_edit.setPlainText)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._after_worker)
        self.worker.start()

    def _after_worker(self):
        """Lance l'aperçu demandé pendant qu'un autre traitement tournait."""
        if self._pending_preview:
            self._pending_preview = False
            self._selection_changed()

    def download_preview(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows or not self.preview_edit.toPlainText():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer le JSON décompressé", "donnees.json", "JSON (*.json)"
        )
        if path:
            Path(path).write_text(self.preview_edit.toPlainText(), encoding="utf-8")
            self.status_label.setText("JSON décompressé enregistré")

    def _set_busy(self, busy, message):
        set_button_busy(self.list_btn, busy)
        set_button_enabled(self.list_btn, not busy)
        set_button_enabled(self.download_btn, not busy and bool(self.table.selectionModel().selectedRows()))
        set_button_enabled(self.output_btn, not busy)
        self.status_label.setText(message)

    def _on_finished(self, message):
        self.progress.setVisible(False)
        self._set_busy(False, message)

    def _on_failed(self, message):
        self._previewed_name = None
        self.progress.setVisible(False)
        self._set_busy(False, "Échec de l'opération")
        QMessageBox.critical(self, "Extraction API", message)

    def choose_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir le dossier de téléchargement")
        if path:
            self.output_edit.setText(path)
