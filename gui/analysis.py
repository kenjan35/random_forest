"""
Fait le pont entre le pipeline (src/predict.py) et l'interface graphique :
lance l'analyse d'un fichier, regroupe les fenêtres en alerte en périodes
lisibles, et prépare les données nécessaires au graphique.
"""

import os
import glob

import numpy as np
import pandas as pd

from src.config import FUEL_COL as FUEL_COLUMN
from src.config import STATUS_COL as STATUS_COLUMN
from src.config import TIME_COL as TIMESTAMP_COLUMN
from src.preprocess import clean_fuel
from src.predict import (
    WINDOW_SIZE,
    GLITCH_REFERENCE_FRACTION,
    confirmed_glitch_mask,
    parse_status,
    predict_arrays,
    _is_active_value as _is_generator_active,  # conservé pour compatibilité
)

TANK_VOLUME_COLUMN = "(MFSX) FSA Total Tank Volume (Ltr) [MFSX:01:1:6] (S1)"

# Fraction minimale d'une période d'alerte devant coïncider avec un
# décrochage capteur pour que l'alerte soit reclassée en "Data incomplete"
# plutôt qu'en vol suspecté.
GLITCH_OVERLAP_THRESHOLD = 0.6

# Une chute à 0 L n'est un décrochage capteur que si le réservoir n'était
# PAS déjà proche de vide juste avant ou juste après (sinon : vraie panne sèche).
GLITCH_BASELINE_RATIO = GLITCH_REFERENCE_FRACTION


class AnalysisError(Exception):
    """Erreur "propre" à afficher telle quelle dans l'interface."""


def group_consecutive(indices):
    """Regroupe des indices triés en intervalles consécutifs [(début, fin), ...]."""
    indices = np.asarray(indices, dtype=np.int64)
    if len(indices) == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) != 1)
    starts = np.concatenate(([indices[0]], indices[breaks + 1]))
    ends = np.concatenate((indices[breaks], [indices[-1]]))
    return list(zip(starts.tolist(), ends.tolist()))


def find_csv_files(folder):
    return sorted(glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True))


def detect_sensor_glitches(fuel):
    """
    Décrochages capteur : le niveau tombe brutalement à 0 L alors que le
    niveau juste avant ou juste après est un niveau réel. Le carburant ne
    "revient" pas tout seul : c'est une coupure de communication ou une
    réinitialisation du capteur. Filtre appliqué a posteriori pour qualifier
    les alertes ; un épisode en tout début de fichier est aussi pris en compte.
    """
    return confirmed_glitch_mask(fuel, include_leading=True)


def _read_tank_capacity(df):
    if TANK_VOLUME_COLUMN not in df.columns:
        return None
    values = pd.to_numeric(df[TANK_VOLUME_COLUMN], errors="coerce").dropna()
    return float(values.median()) if not values.empty else None


def analyze_file(csv_path):
    """
    Lance la prédiction sur un fichier et retourne toutes les infos
    nécessaires à l'affichage (résumé + périodes + données du graphique).
    Lève AnalysisError avec un message clair en cas de problème (modèle
    manquant, colonnes absentes, fichier illisible, etc.).
    """
    if not os.path.exists(csv_path):
        raise AnalysisError(f"Fichier introuvable : {csv_path}")

    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise AnalysisError(f"Impossible de lire le CSV : {exc}") from exc

    missing = [c for c in (FUEL_COLUMN, STATUS_COLUMN, TIMESTAMP_COLUMN) if c not in df.columns]
    if missing:
        raise AnalysisError(
            "Colonne(s) attendue(s) absente(s) de ce fichier :\n" + "\n".join(missing)
        )

    # le CSV n'est lu qu'une fois : les mêmes données servent au modèle et au graphique
    fuel = clean_fuel(df[FUEL_COLUMN])
    status = df[STATUS_COLUMN].to_numpy()
    timestamps = df[TIMESTAMP_COLUMN].to_numpy()

    try:
        prediction = predict_arrays(fuel, status)
    except FileNotFoundError as exc:
        raise AnalysisError(
            "Modèle introuvable (model/random_forest.pkl).\n"
            "Lancez d'abord `python main.py` pour entraîner et sauvegarder le modèle."
        ) from exc
    except Exception as exc:
        raise AnalysisError(f"Erreur pendant l'analyse : {exc}") from exc

    n_rows = len(fuel)
    glitch_mask = detect_sensor_glitches(fuel)

    def make_event(row_start, row_end, glitch_ratio=0.0):
        row_start, row_end = int(row_start), int(row_end)
        return {
            "row_start": row_start,
            "row_end": row_end,
            "ts_start": str(timestamps[row_start]),
            "ts_end": str(timestamps[row_end]),
            "glitch_ratio": round(float(glitch_ratio), 2),
            "fuel_drop": round(float(fuel[row_start] - fuel[row_end]), 1),
        }

    events, events_ignored = [], []
    for window_start, window_end in group_consecutive(np.flatnonzero(prediction == 1)):
        row_start = window_start
        row_end = min(window_end + WINDOW_SIZE - 1, n_rows - 1)
        glitch_ratio = float(glitch_mask[row_start:row_end + 1].mean())
        event = make_event(row_start, row_end, glitch_ratio)
        # L'alerte coïncide surtout avec un décrochage capteur : on l'écarte du
        # décompte des vols mais on la garde visible, à part.
        (events_ignored if glitch_ratio >= GLITCH_OVERLAP_THRESHOLD else events).append(event)

    # Ajoute les pannes capteur qui n'ont pas déjà été signalées via une alerte
    # (c'est bien un cas "Data incomplete" et non un "Aucun vol détecté").
    covered = [(ev["row_start"], ev["row_end"]) for ev in events_ignored]
    for start, end in group_consecutive(np.flatnonzero(glitch_mask)):
        if not any(s <= start and end <= e for s, e in covered):
            events_ignored.append(make_event(start, end, 1.0))
    events_ignored.sort(key=lambda ev: ev["row_start"])

    has_sensor_glitch = len(events_ignored) > 0
    return {
        "csv_path": csv_path,
        "filename": os.path.basename(csv_path),
        "fuel": fuel,
        "status": status,
        "active": parse_status(status, n_rows),
        "tank_capacity": _read_tank_capacity(df),
        "timestamps": timestamps,
        "n_rows": n_rows,
        "n_windows": int(len(prediction)),
        "n_alert_windows": int(prediction.sum()),
        "events": events,
        "n_events": len(events),
        "events_ignored": events_ignored,
        "n_events_ignored": len(events_ignored),
        "has_theft": len(events) > 0,
        "has_sensor_glitch": has_sensor_glitch,
        "has_issue": len(events) > 0 or has_sensor_glitch,
    }
