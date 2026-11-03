"""
Installateur graphique de Fuel Theft Detector (lancé par installer.bat).

Utilise uniquement la bibliothèque standard (tkinter) : il fonctionne avant que
les dépendances de l'application (PySide6, etc.) ne soient installées.
Étapes : vérification de Python, environnement virtuel, pip, dépendances,
vérification, raccourci sur le Bureau.
"""

import math
import os
import queue
import shutil
import subprocess
import sys
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "venv")
REQUIREMENTS = os.path.join(BASE_DIR, "requirements-gui.txt")
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")
APP_NAME = "Fuel Theft Detector"
MIN_PYTHON = (3, 9)
IS_WINDOWS = sys.platform == "win32"
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0   # CREATE_NO_WINDOW : pas de console noire qui clignote

# modules à importer pour vérifier l'installation (nom affiché, module)
CHECK_MODULES = [("PySide6", "PySide6"), ("pandas", "pandas"), ("scikit-learn", "sklearn"),
                 ("matplotlib", "matplotlib"), ("reportlab", "reportlab"), ("python-docx", "docx"),
                 ("openpyxl", "openpyxl"), ("selenium", "selenium"), ("minio", "minio")]

STEPS = [
    ("python", "Vérification de Python", 0, 3),
    ("venv", "Création de l'environnement de l'application", 3, 12),
    ("pip", "Mise à jour de l'outil d'installation (pip)", 12, 15),
    ("deps", "Installation des composants (peut prendre plusieurs minutes)", 15, 90),
    ("check", "Vérification de l'installation", 90, 97),
    ("shortcut", "Création du raccourci sur le Bureau", 97, 100),
]


def venv_python(gui=False):
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "pythonw.exe" if gui else "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


class InstallCancelled(Exception):
    pass


class InstallError(Exception):
    pass


class Installer:
    """
    Logique d'installation, sans interface : exécutée dans un fil séparé, elle
    envoie des évènements dans `events` (lus par l'interface) :
      ("step", clé, état, détail)   état : "running" | "done" | "skipped" | "error"
      ("progress", pourcentage, texte)
      ("log", ligne)
      ("finished", succès, message)
    """

    def __init__(self, events, create_shortcut=True, requirements=REQUIREMENTS):
        self.events = events
        self.create_shortcut = create_shortcut
        self.requirements = requirements
        self._process = None
        self._cancelled = False

    # -------------------------------------------------------------- outils

    def emit(self, *event):
        self.events.put(event)

    def log(self, line):
        self.emit("log", line.rstrip())

    def cancel(self):
        self._cancelled = True
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()

    def _check_cancel(self):
        if self._cancelled:
            raise InstallCancelled()

    def run_command(self, args, on_line=None):
        """Exécute une commande, transmet chaque ligne de sortie au journal."""
        self._check_cancel()
        self.log("> " + " ".join(f'"{a}"' if " " in a else a for a in args))
        env = dict(os.environ, PYTHONUNBUFFERED="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
        self._process = subprocess.Popen(
            args, cwd=BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
            creationflags=NO_WINDOW, env=env,
        )
        tail = []
        for line in self._process.stdout:
            line = line.rstrip()
            if not line:
                continue
            self.log(line)
            tail = (tail + [line])[-15:]
            if on_line:
                on_line(line)
        code = self._process.wait()
        self._process = None
        self._check_cancel()
        if code != 0:
            raise InstallError(self._explain_failure("\n".join(tail), code))

    @staticmethod
    def _explain_failure(tail, code):
        text = tail.lower()
        if any(s in text for s in ("connection", "timed out", "name resolution", "getaddrinfo",
                                   "proxy", "ssl", "certificate", "no matching distribution")):
            return ("Téléchargement impossible : vérifiez la connexion Internet "
                    "(ou le proxy de l'entreprise), puis cliquez sur « Réessayer ».")
        if "permission" in text or "access is denied" in text or "accès refusé" in text:
            return ("Accès refusé à un fichier : fermez l'application si elle est ouverte, "
                    "puis cliquez sur « Réessayer ».")
        if "no space" in text or "espace" in text:
            return "Espace disque insuffisant."
        return f"La commande a échoué (code {code}). Consultez les détails ci-dessous."

    def step(self, key, state, detail=""):
        self.emit("step", key, state, detail)

    def progress(self, key, fraction, text=""):
        _k, _label, start, end = next(s for s in STEPS if s[0] == key)
        self.emit("progress", start + (end - start) * max(0.0, min(1.0, fraction)), text)

    # -------------------------------------------------------------- étapes

    def check_python(self):
        version = sys.version_info
        detail = f"Python {version.major}.{version.minor}.{version.micro}"
        if version < MIN_PYTHON:
            raise InstallError(f"{detail} est trop ancien : installez Python "
                               f"{MIN_PYTHON[0]}.{MIN_PYTHON[1]} ou plus récent depuis python.org.")
        if sys.maxsize <= 2 ** 32:
            raise InstallError(f"{detail} est en version 32 bits : installez la version 64 bits "
                               "de Python (nécessaire pour l'interface graphique).")
        return detail

    def ensure_venv(self):
        python = venv_python()
        if os.path.exists(python):
            return "déjà présent"
        if os.path.isdir(VENV_DIR):
            self.log("Environnement incomplet : suppression puis recréation.")
            shutil.rmtree(VENV_DIR, ignore_errors=True)
        self.run_command([sys.executable, "-m", "venv", VENV_DIR])
        if not os.path.exists(python):
            raise InstallError("L'environnement de l'application n'a pas pu être créé.")
        return "créé"

    def upgrade_pip(self):
        self.run_command([venv_python(), "-m", "pip", "install", "--upgrade", "pip"])
        return "à jour"

    def install_dependencies(self):
        if not os.path.exists(self.requirements):
            raise InstallError(f"Fichier introuvable : {os.path.basename(self.requirements)}")
        counter = {"collected": 0, "current": ""}

        def on_line(line):
            words = line.split()
            if line.startswith("Collecting ") and len(words) > 1:
                counter["collected"] += 1
                counter["current"] = words[1]
                # progression estimée : on ne connaît pas d'avance le nombre total de paquets
                fraction = 0.85 * (1 - math.exp(-counter["collected"] / 18))
                self.progress("deps", fraction, f"Téléchargement : {counter['current']}")
            elif line.startswith("Requirement already satisfied") and len(words) > 3:
                counter["collected"] += 1
                fraction = 0.85 * (1 - math.exp(-counter["collected"] / 18))
                self.progress("deps", fraction, f"Déjà présent : {words[3]}")
            elif line.startswith("Installing collected packages"):
                self.progress("deps", 0.9, "Installation des composants téléchargés…")
            elif line.startswith("Successfully installed"):
                self.progress("deps", 1.0, "Composants installés")

        self.run_command([venv_python(), "-m", "pip", "install", "-r", self.requirements], on_line)
        return f"{counter['collected']} composant(s)"

    def verify(self):
        script = ("import importlib, sys\n"
                  f"mods = {CHECK_MODULES!r}\n"
                  "missing = []\n"
                  "for label, name in mods:\n"
                  "    try:\n"
                  "        importlib.import_module(name)\n"
                  "    except Exception as exc:\n"
                  "        missing.append(f'{label} ({type(exc).__name__}: {exc})')\n"
                  "print('MANQUANT: ' + '; '.join(missing) if missing else 'OK')\n"
                  "sys.exit(1 if missing else 0)\n")
        try:
            self.run_command([venv_python(), "-c", script])
        except InstallError:
            raise InstallError("Certains composants ne se chargent pas (voir les détails). "
                               "Cliquez sur « Réessayer » ; si le problème persiste, supprimez "
                               "le dossier « venv » puis relancez l'installation.")
        return "tout fonctionne"

    def make_shortcut(self):
        if not self.create_shortcut:
            return None
        if not IS_WINDOWS:
            return "ignoré (Windows uniquement)"
        def q(text):   # chaîne PowerShell entre apostrophes (un ' devient '')
            return "'" + str(text).replace("'", "''") + "'"

        target = venv_python(gui=True)
        script = os.path.join(BASE_DIR, "gui_app.py")
        ps = (
            "$desktop = [Environment]::GetFolderPath('Desktop');"
            "$shell = New-Object -ComObject WScript.Shell;"
            f"$link = $shell.CreateShortcut((Join-Path $desktop {q(APP_NAME + '.lnk')}));"
            f"$link.TargetPath = {q(target)};"
            f"$link.Arguments = {q(chr(34) + script + chr(34))};"
            f"$link.WorkingDirectory = {q(BASE_DIR)};"
            + (f"$link.IconLocation = {q(ICON_PATH)};" if os.path.exists(ICON_PATH) else "")
            + f"$link.Description = {q(APP_NAME)};"
            "$link.Save()"
        )
        self.run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps])
        return "créé"

    # ---------------------------------------------------------- déroulement

    def run(self):
        actions = {
            "python": self.check_python, "venv": self.ensure_venv, "pip": self.upgrade_pip,
            "deps": self.install_dependencies, "check": self.verify, "shortcut": self.make_shortcut,
        }
        current = None
        try:
            for key, label, _start, _end in STEPS:
                current = key
                self._check_cancel()
                self.step(key, "running")
                self.progress(key, 0.0, label + "…")
                detail = actions[key]()
                self.step(key, "skipped" if detail is None else "done", detail or "non demandé")
                self.progress(key, 1.0)
            self.emit("finished", True, "L'application est installée et prête à l'emploi.")
        except InstallCancelled:
            if current:
                self.step(current, "error", "annulé")
            self.emit("finished", False, "Installation annulée.")
        except InstallError as exc:
            self.step(current, "error", "échec")
            self.emit("finished", False, str(exc))
        except Exception as exc:  # erreur imprévue : on l'affiche plutôt que de fermer
            self.step(current, "error", "échec")
            self.log(f"{type(exc).__name__}: {exc}")
            self.emit("finished", False, f"Erreur inattendue : {exc}")


# =====================================================================
# Interface
# =====================================================================

ACCENT = "#1caae2"
ACCENT_DARK = "#1690bd"
BG = "#f8fafc"
TEXT = "#0f172a"
MUTED = "#64748b"
OK = "#16a34a"
ERROR = "#dc2626"
ICONS = {"pending": ("○", MUTED), "running": ("●", ACCENT), "done": ("✓", OK),
         "skipped": ("–", MUTED), "error": ("✕", ERROR)}


def create_window(title, subtitle):
    """Fenêtre commune à l'installateur et au désinstallateur (styles + bandeau)."""
    import tkinter as tk
    from tkinter import ttk

    if IS_WINDOWS:
        try:  # texte net sur les écrans haute résolution (à faire avant de créer la fenêtre)
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    root.title(title)
    root.configure(bg=BG)
    root.resizable(False, False)
    if IS_WINDOWS and os.path.exists(ICON_PATH):
        try:
            root.iconbitmap(ICON_PATH)
        except tk.TclError:
            pass
    font = "Segoe UI" if IS_WINDOWS else "DejaVu Sans"
    mono = "Consolas" if IS_WINDOWS else "DejaVu Sans Mono"
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT, font=(font, 10))
    style.configure("Muted.TLabel", foreground=MUTED, font=(font, 9))
    style.configure("Status.TLabel", font=(font, 10, "bold"))
    style.configure("TCheckbutton", background=BG, foreground=TEXT, font=(font, 10))
    style.map("TCheckbutton", background=[("active", BG)])
    style.configure("Accent.Horizontal.TProgressbar", troughcolor="#e2e8f0", background=ACCENT,
                    bordercolor="#e2e8f0", lightcolor=ACCENT, darkcolor=ACCENT, thickness=10)
    style.configure("Primary.TButton", font=(font, 10, "bold"), foreground="white", background=ACCENT,
                    borderwidth=0, padding=(18, 8))
    style.map("Primary.TButton", background=[("disabled", "#cbd5e1"), ("active", ACCENT_DARK)],
              foreground=[("disabled", "#f1f5f9")])
    style.configure("Danger.TButton", font=(font, 10, "bold"), foreground="white", background=ERROR,
                    borderwidth=0, padding=(18, 8))
    style.map("Danger.TButton", background=[("disabled", "#cbd5e1"), ("active", "#b91c1c")],
              foreground=[("disabled", "#f1f5f9")])
    style.configure("Secondary.TButton", font=(font, 10), foreground=TEXT, background="white",
                    bordercolor="#cbd5e1", padding=(14, 8))
    style.map("Secondary.TButton", background=[("active", "#f1f5f9")])
    style.configure("Link.TButton", font=(font, 9), foreground=ACCENT_DARK, background=BG,
                    borderwidth=0, padding=(0, 2))
    style.map("Link.TButton", background=[("active", BG)])

    header = tk.Frame(root, bg=ACCENT, padx=24, pady=18)
    header.pack(fill="x")
    tk.Label(header, text=APP_NAME, bg=ACCENT, fg="white", font=(font, 17, "bold")).pack(anchor="w")
    tk.Label(header, text=subtitle, bg=ACCENT, fg="#e0f4fc", font=(font, 10)).pack(anchor="w")
    return tk, ttk, root, font, mono


def center_window(root):
    root.update_idletasks()
    width, height = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry(f"+{(root.winfo_screenwidth() - width) // 2}+{(root.winfo_screenheight() - height) // 3}")


def run_gui():
    tk, ttk, root, font, mono = create_window(f"Installation — {APP_NAME}", "Installation de l'application")

    body = ttk.Frame(root, padding=(24, 18, 24, 8))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="Cet assistant prépare tout ce dont l'application a besoin. Une connexion "
                         "Internet est nécessaire. Aucun droit administrateur n'est requis.",
              wraplength=500, justify="left").pack(anchor="w", pady=(0, 14))

    # ---- liste des étapes
    step_rows = {}
    steps_frame = ttk.Frame(body)
    steps_frame.pack(fill="x")
    for key, label, _s, _e in STEPS:
        row = ttk.Frame(steps_frame)
        row.pack(fill="x", pady=2)
        icon = tk.Label(row, text="○", bg=BG, fg=MUTED, font=(font, 11, "bold"), width=2)
        icon.pack(side="left")
        text = ttk.Label(row, text=label)
        text.pack(side="left")
        detail = ttk.Label(row, text="", style="Muted.TLabel")
        detail.pack(side="right")
        step_rows[key] = (icon, text, detail)

    # ---- progression
    progress_var = tk.DoubleVar(value=0)
    ttk.Progressbar(body, variable=progress_var, maximum=100, length=500,
                    style="Accent.Horizontal.TProgressbar").pack(fill="x", pady=(16, 6))
    status_var = tk.StringVar(value="Prêt à installer.")
    status = ttk.Label(body, textvariable=status_var, style="Status.TLabel", wraplength=500, justify="left")
    status.pack(anchor="w")

    # ---- options
    options = ttk.Frame(body)
    options.pack(fill="x", pady=(12, 0))
    shortcut_var = tk.BooleanVar(value=IS_WINDOWS)
    launch_var = tk.BooleanVar(value=True)
    shortcut_box = ttk.Checkbutton(options, text="Créer un raccourci sur le Bureau", variable=shortcut_var)
    shortcut_box.pack(anchor="w")
    launch_box = ttk.Checkbutton(options, text="Lancer l'application à la fin", variable=launch_var)
    launch_box.pack(anchor="w")
    if not IS_WINDOWS:
        shortcut_box.state(["disabled"])

    # ---- journal détaillé (masqué par défaut)
    details_button = ttk.Button(body, text="▸ Afficher les détails", style="Link.TButton")
    details_button.pack(anchor="w", pady=(10, 0))
    log_frame = ttk.Frame(body)
    log_text = tk.Text(log_frame, height=10, width=70, font=(mono, 8), bg="#0f172a", fg="#e2e8f0",
                       relief="flat", padx=8, pady=6, wrap="none", state="disabled")
    log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
    log_text.configure(yscrollcommand=log_scroll.set)
    log_text.pack(side="left", fill="both", expand=True)
    log_scroll.pack(side="right", fill="y")

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

    # ---- boutons
    footer = ttk.Frame(root, padding=(24, 10, 24, 18))
    footer.pack(fill="x")
    close_button = ttk.Button(footer, text="Fermer", style="Secondary.TButton", command=root.destroy)
    close_button.pack(side="right")
    main_button = ttk.Button(footer, text="Installer", style="Primary.TButton")
    main_button.pack(side="right", padx=(0, 10))

    events = queue.Queue()
    state = {"installer": None, "finished": False, "success": False}

    def reset_steps():
        for icon, _text, detail in step_rows.values():
            icon.configure(text=ICONS["pending"][0], fg=ICONS["pending"][1])
            detail.configure(text="")

    def start():
        reset_steps()
        progress_var.set(0)
        status.configure(foreground=TEXT)
        status_var.set("Installation en cours…")
        installer = Installer(events, create_shortcut=shortcut_var.get())
        state.update(installer=installer, finished=False)
        main_button.configure(text="Installation…")
        main_button.state(["disabled"])
        close_button.configure(text="Annuler", command=cancel)
        shortcut_box.state(["disabled"])
        threading.Thread(target=installer.run, daemon=True).start()

    def cancel():
        installer = state["installer"]
        if installer is not None and not state["finished"]:
            status_var.set("Annulation…")
            installer.cancel()

    def launch_app():
        if IS_WINDOWS:
            subprocess.Popen([venv_python(gui=True), os.path.join(BASE_DIR, "gui_app.py")], cwd=BASE_DIR,
                             creationflags=NO_WINDOW)
        else:
            subprocess.Popen([venv_python(), os.path.join(BASE_DIR, "gui_app.py")], cwd=BASE_DIR)
        root.destroy()

    def on_finished(success, message):
        state.update(finished=True, success=success)
        progress_var.set(100 if success else progress_var.get())
        status_var.set(message)
        status.configure(foreground=OK if success else ERROR)
        close_button.configure(text="Fermer", command=root.destroy)
        main_button.state(["!disabled"])
        if IS_WINDOWS:
            shortcut_box.state(["!disabled"])
        if success:
            if launch_var.get():
                main_button.configure(text="Lancer l'application", command=launch_app)
                root.after(800, launch_app)
            else:
                main_button.configure(text="Lancer l'application", command=launch_app)
        else:
            main_button.configure(text="Réessayer", command=start)
            if "annulée" not in message:
                toggle_details(True)

    def poll():
        try:
            while True:
                event = events.get_nowait()
                kind = event[0]
                if kind == "log":
                    log_text.configure(state="normal")
                    log_text.insert("end", event[1] + "\n")
                    if int(log_text.index("end-1c").split(".")[0]) > 3000:   # journal borné
                        log_text.delete("1.0", "500.0")
                    log_text.see("end")
                    log_text.configure(state="disabled")
                elif kind == "step":
                    _kind, key, step_state, detail = event
                    icon, _text, detail_label = step_rows[key]
                    glyph, color = ICONS[step_state]
                    icon.configure(text=glyph, fg=color)
                    detail_label.configure(text=detail)
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
        if state["installer"] is not None and not state["finished"]:
            cancel()
            root.after(300, root.destroy)
        else:
            root.destroy()

    main_button.configure(command=start)
    root.protocol("WM_DELETE_WINDOW", on_close)
    if os.path.exists(venv_python()):
        status_var.set("Une installation existe déjà : « Installer » la met à jour ou la répare.")
    root.after(100, poll)
    center_window(root)
    root.mainloop()


if __name__ == "__main__":
    run_gui()
