"""
Constantes partagées par tout le projet (une seule source de vérité).
"""

import os

# Racine du projet (dossier qui contient src/, model/, data/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_DIR = os.path.join(BASE_DIR, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "random_forest.pkl")
THRESHOLD_PATH = os.path.join(MODEL_DIR, "threshold.pkl")
DEFAULT_THRESHOLD = 0.5

# Taille des fenêtres glissantes vues par le modèle (NE PAS MODIFIER sans
# réentraîner : le modèle existant a été appris avec cette valeur)
WINDOW_SIZE = 20

# Colonnes des exports MFSX
FUEL_COL = "(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"
STATUS_COL = "FSA Generator Running [MFSX:01:1:12] (S2)"
TIME_COL = "Time stamp"
