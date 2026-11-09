"""
Désinstallateur graphique de Fuel Theft Detector (lancé par uninstaller.bat).

Supprime ce que installer.bat a créé :
  - le raccourci « Fuel Theft Detector » du Bureau (seulement s'il pointe vers ce dossier) ;
  - l'environnement de l'application (dossier « venv » : PySide6, pandas, etc.) ;
  - les fichiers temporaires Python (dossiers « __pycache__ »).
En option : l'historique du Dashboard (data/site_history.db).

Ne touche jamais au code, au modèle (model/), aux données (data/*.csv, extractions)
ni aux rapports. Doit être lancé avec le Python du système, pas celui du venv.
"""

import os
import queue
import stat
import subprocess
import sys
import threading

import installer_gui as common
from installer_gui import APP_NAME, BASE_DIR, IS_WINDOWS, NO_WINDOW, VENV_DIR
from uninstaller_utils import ps_quote

_ps_quote = ps_quote

HISTORY_DB = os.path.join(BASE_DIR, "data", "site_history.db")

STEPS = [
    ("app", "Vérification que l'application est fermée", 0, 5),
    ("shortcut", "Suppression du raccourci du Bureau", 5, 10),
    ("venv", "Suppression de l'environnement de l'application", 10, 90),
    ("cache", "Suppression des fichiers temporaires", 90, 97),
    ("history", "Suppression de l'historique du Dashboard", 97, 100),
]


class UninstallCancelled(Exception):
    pass


class UninstallError(Exception):
    pass


def _powershell(command):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=NO_WINDOW,
    )
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


def running_app_processes():
    """Processus Python lancés depuis le venv de CE dossier (l'application ouverte)."""
    if not IS_WINDOWS:
        return []
    code, out, _err = _powershell(
        "Get-Process python,pythonw -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.Path -like ({ps_quote(VENV_DIR)} + '*') }} | "
        "ForEach-Object { $_.Id }"
    )
    return [int(pid) for pid in out.split() if pid.isdigit()] if code == 0 else []


def stop_processes(pids):
    if pids and IS_WINDOWS:
        _powershell(f"Stop-Process -Id {','.join(str(p) for p in pids)} -Force -ErrorAction SilentlyContinue")


class Uninstaller:
    """Logique de désinstallation, sans interface (même principe que installer_gui.Installer)."""

    def __init__(self, events, remove_history=False):
        self.events = events
        self.remove_history = remove_history
        self._cancelled = False

    def emit(self, *event):
        self.events.put(event)

    def log(self, line):
        self.emit("log", line)

    def cancel(self):
        self._cancelled = True

    def _check_cancel(self):
        if self._cancelled:
            raise UninstallCancelled()

    def progress(self, key, fraction, text=""):
        _k, _label, start, end = next(s for s in STEPS if s[0] == key)
        self.emit("progress", start + (end - start) * max(0.0, min(1.0, fraction)), text)

    # -------------------------------------------------------------- étapes

    def check_app_closed(self):
        if running_app_processes():
            raise UninstallError("L'application est encore ouverte : fermez-la, puis cliquez sur « Réessayer ».")
        return "fermée"

    def remove_shortcut(self):
        if not IS_WINDOWS:
            return "aucun"
        # on ne supprime le raccourci que s'il lance bien l'application de CE dossier
        code, out, err = _powershell(
            "$desktop = [Environment]::GetFolderPath('Desktop');"
            f"$path = Join-Path $desktop {_ps_quote(APP_NAME + '.lnk')};"
            "if (-not (Test-Path -LiteralPath $path)) { 'ABSENT'; exit 0 }"
            "$target = (New-Object -ComObject WScript.Shell).CreateShortcut($path).TargetPath;"
            f"if ($target -like ({_ps_quote(BASE_DIR)} + '*')) {{ Remove-Item -LiteralPath $path -Force; 'SUPPRIME' }}"
            " else { 'AUTRE' }"
        )
        self.log(f"Raccourci : {out or err}")
        if code != 0:
            raise UninstallError(f"Impossible de supprimer le raccourci : {err or out}")
        return {"ABSENT": "aucun", "SUPPRIME": "supprimé", "AUTRE": "conservé (autre installation)"}.get(out, out)

    def _delete_tree(self, root, key):
        """Supprime un dossier fichier par fichier (progression + fichiers en lecture seule)."""
        files = []
        for folder, dirs, names in os.walk(root, topdown=False):
            files.extend(os.path.join(folder, n) for n in names)
        total = max(1, len(files))
        locked = []
        for i, path in enumerate(files, start=1):
            self._check_cancel()
            try:
                os.remove(path)
            except PermissionError:
                try:
                    os.chmod(path, stat.S_IWRITE)   # fichier en lecture seule
                    os.remove(path)
                except OSError:
                    locked.append(path)
            except FileNotFoundError:
                pass
            if i % 200 == 0 or i == total:
                self.progress(key, i / total, f"Suppression… {i:,} / {total:,} fichiers".replace(",", " "))
        for folder, dirs, _names in os.walk(root, topdown=False):
            for d in dirs:
                try:
                    os.rmdir(os.path.join(folder, d))
                except OSError:
                    pass
        try:
            os.rmdir(root)
        except OSError:
            pass
        return files, locked

    def remove_venv(self):
        if not os.path.isdir(VENV_DIR):
            return "déjà absent"
        files, locked = self._delete_tree(VENV_DIR, "venv")
        if locked:
            for path in locked[:10]:
                self.log(f"Verrouillé : {path}")
            raise UninstallError(f"{len(locked)} fichier(s) sont utilisés par un autre programme. "
                                 "Fermez l'application (et tout terminal Python), puis cliquez sur « Réessayer ».")
        return f"{len(files):,} fichiers supprimés".replace(",", " ")

    def remove_caches(self):
        removed = 0
        for folder, dirs, _names in os.walk(BASE_DIR):
            if os.path.abspath(folder).startswith(os.path.abspath(VENV_DIR)):
                dirs[:] = []
                continue
            for d in list(dirs):
                if d == "__pycache__":
                    self._delete_tree(os.path.join(folder, d), "cache")
                    dirs.remove(d)
                    removed += 1
        return f"{removed} dossier(s)" if removed else "rien à supprimer"

    def remove_history_db(self):
        if not self.remove_history:
            return None
        if not os.path.exists(HISTORY_DB):
            return "déjà absent"
        os.remove(HISTORY_DB)
        return "supprimé"

    def run(self):
        actions = {"app": self.check_app_closed, "shortcut": self.remove_shortcut, "venv": self.remove_venv,
                   "cache": self.remove_caches, "history": self.remove_history_db}
        current = None
        try:
            for key, label, _s, _e in STEPS:
                current = key
                self._check_cancel()
                self.emit("step", key, "running", "")
                self.progress(key, 0.0, label + "…")
                detail = actions[key]()
                self.emit("step", key, "skipped" if detail is None else "done", detail or "conservé")
                self.progress(key, 1.0)
            self.emit("finished", True, "Désinstallation terminée.")
        except UninstallCancelled:
            self.emit("step", current, "error", "interrompu")
            self.emit("finished", False, "Désinstallation interrompue : relancez-la pour terminer le nettoyage.")
        except UninstallError as exc:
            self.emit("step", current, "error", "échec")
            self.emit("finished", False, str(exc))
        except Exception as exc:
            self.emit("step", current, "error", "échec")
            self.log(f"{type(exc).__name__}: {exc}")
            self.emit("finished", False, f"Erreur inattendue : {exc}")


# =====================================================================
# Interface
# =====================================================================

def run_gui():
    tk, ttk, root, font, mono = common.create_window(f"Désinstallation — {APP_NAME}",
                                                     "Désinstallation de l'application")
    from tkinter import messagebox

    body = ttk.Frame(root, padding=(24, 18, 24, 8))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Cet assistant supprime ce qui a été installé par installer.bat : "
                         "l'environnement de l'application et le raccourci du Bureau.",
              wraplength=500, justify="left").pack(anchor="w", pady=(0, 6))
    ttk.Label(body, text="Conservés : le code, le modèle, vos données et vos rapports. "
                         "Vous pourrez réinstaller à tout moment avec installer.bat.",
              style="Muted.TLabel", wraplength=500, justify="left").pack(anchor="w", pady=(0, 14))

    step_rows = {}
    steps_frame = ttk.Frame(body)
    steps_frame.pack(fill="x")
    for key, label, _s, _e in STEPS:
        row = ttk.Frame(steps_frame)
        row.pack(fill="x", pady=2)
        icon = tk.Label(row, text="○", bg=common.BG, fg=common.MUTED, font=(font, 11, "bold"), width=2)
        icon.pack(side="left")
        ttk.Label(row, text=label).pack(side="left")
        detail = ttk.Label(row, text="", style="Muted.TLabel")
        detail.pack(side="right")
        step_rows[key] = (icon, detail)

    progress_var = tk.DoubleVar(value=0)
    ttk.Progressbar(body, variable=progress_var, maximum=100, length=500,
                    style="Accent.Horizontal.TProgressbar").pack(fill="x", pady=(16, 6))
    status_var = tk.StringVar(value="Prêt à désinstaller.")
    status = ttk.Label(body, textvariable=status_var, style="Status.TLabel", wraplength=500, justify="left")
    status.pack(anchor="w")

    history_var = tk.BooleanVar(value=False)
    history_box = ttk.Checkbutton(body, variable=history_var,
                                  text="Supprimer aussi l'historique du Dashboard (sites, vols enregistrés)")
    history_box.pack(anchor="w", pady=(12, 0))
    if not os.path.exists(HISTORY_DB):
        history_box.state(["disabled"])

    details_button = ttk.Button(body, text="▸ Afficher les détails", style="Link.TButton")
    details_button.pack(anchor="w", pady=(10, 0))
    log_frame = ttk.Frame(body)
    log_text = tk.Text(log_frame, height=8, width=70, font=(mono, 8), bg="#0f172a", fg="#e2e8f0",
                       relief="flat", padx=8, pady=6, wrap="none", state="disabled")
    log_text.pack(fill="both", expand=True)

    def toggle_details(force=None):
        visible = log_frame.winfo_ismapped()
        show = (not visible) if force is None else force
        if show and not visible:
            log_frame.pack(fill="both", expand=True, pady=(6, 0), after=details_button)
            details_button.configure(text="▾ Masquer les détails")
        elif not show and visible:
            log_frame.pack_forget()
            details_button.configure(text="▸ Afficher les détails")

    details_button.configure(command=toggle_details)

    footer = ttk.Frame(root, padding=(24, 10, 24, 18))
    footer.pack(fill="x")
    close_button = ttk.Button(footer, text="Fermer", style="Secondary.TButton", command=root.destroy)
    close_button.pack(side="right")
    main_button = ttk.Button(footer, text="Désinstaller", style="Danger.TButton")
    main_button.pack(side="right", padx=(0, 10))

    events = queue.Queue()
    state = {"worker": None, "finished": False}

    def start():
        pids = running_app_processes()
        if pids:
            if not messagebox.askyesno(
                    "Application ouverte",
                    f"{APP_NAME} est encore ouverte.\n\nLa fermer maintenant pour continuer ?\n"
                    "(les travaux non enregistrés seront perdus)", parent=root):
                return
            stop_processes(pids)
        elif state["worker"] is None and not messagebox.askyesno(
                "Confirmer la désinstallation",
                f"Supprimer l'environnement de {APP_NAME} et son raccourci ?\n\n"
                "Vos données, le modèle et les rapports sont conservés.", parent=root):
            return
        for icon, detail in step_rows.values():
            icon.configure(text="○", fg=common.MUTED)
            detail.configure(text="")
        progress_var.set(0)
        status.configure(foreground=common.TEXT)
        status_var.set("Désinstallation en cours…")
        worker = Uninstaller(events, remove_history=history_var.get())
        state.update(worker=worker, finished=False)
        main_button.state(["disabled"])
        history_box.state(["disabled"])
        close_button.configure(text="Arrêter", command=worker.cancel)
        threading.Thread(target=worker.run, daemon=True).start()

    def open_folder():
        if IS_WINDOWS:
            os.startfile(BASE_DIR)  # noqa: S606 (ouvre l'explorateur Windows)
        root.destroy()

    def on_finished(success, message):
        state["finished"] = True
        status_var.set(message)
        status.configure(foreground=common.OK if success else common.ERROR)
        close_button.configure(text="Fermer", command=root.destroy)
        main_button.state(["!disabled"])
        if success:
            progress_var.set(100)
            status_var.set(message + "\nPour retirer complètement l'application, supprimez ensuite "
                                     f"le dossier :\n{BASE_DIR}")
            main_button.configure(text="Ouvrir le dossier", style="Primary.TButton", command=open_folder)
        else:
            main_button.configure(text="Réessayer", command=start)
            toggle_details(True)

    def poll():
        try:
            while True:
                event = events.get_nowait()
                kind = event[0]
                if kind == "log":
                    log_text.configure(state="normal")
                    log_text.insert("end", event[1] + "\n")
                    log_text.see("end")
                    log_text.configure(state="disabled")
                elif kind == "step":
                    _kind, key, step_state, detail_text = event
                    icon, detail = step_rows[key]
                    glyph, color = common.ICONS[step_state]
                    icon.configure(text=glyph, fg=color)
                    detail.configure(text=detail_text)
                elif kind == "progress":
                    progress_var.set(event[1])
                    if event[2]:
                        status_var.set(event[2])
                elif kind == "finished":
                    on_finished(event[1], event[2])
        except queue.Empty:
            pass
        root.after(100, poll)

    def on_close():
        worker = state["worker"]
        if worker is not None and not state["finished"]:
            worker.cancel()
            root.after(300, root.destroy)
        else:
            root.destroy()

    main_button.configure(command=start)
    root.protocol("WM_DELETE_WINDOW", on_close)
    if not os.path.isdir(VENV_DIR):
        status_var.set("L'application ne semble pas installée (pas de dossier « venv »). "
                       "La désinstallation nettoiera le raccourci et les fichiers temporaires.")
    root.after(100, poll)
    common.center_window(root)
    root.mainloop()


if __name__ == "__main__":
    if os.path.abspath(sys.prefix).startswith(os.path.abspath(VENV_DIR)):
        # lancé depuis le venv qu'on veut supprimer : impossible (fichiers verrouillés)
        print("Relancez uninstaller.bat (le désinstallateur ne peut pas utiliser l'environnement à supprimer).")
        sys.exit(1)
    run_gui()
