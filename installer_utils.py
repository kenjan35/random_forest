"""Small platform helpers shared by the installer entry point."""

import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, "venv")
IS_WINDOWS = sys.platform == "win32"


def venv_python(gui=False):
    if IS_WINDOWS:
        return os.path.join(VENV_DIR, "Scripts", "pythonw.exe" if gui else "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")


def explain_failure(tail, code):
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
