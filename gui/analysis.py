"""
Fait le pont entre le pipeline (src/predict.py) et l'interface graphique :
lance l'analyse d'un fichier, regroupe les fenêtres en alerte en périodes
lisibles, et prépare les données nécessaires au graphique.
"""

import os

import pandas as pd

from gui.analysis_utils import (
    GLITCH_BASELINE_RATIO,
    GLITCH_OVERLAP_THRESHOLD,
    TANK_VOLUME_COLUMN,
    detect_sensor_glitches,
    find_csv_files,
)
from gui.analysis_utils import read_tank_capacity
from gui.analysis_utils_1 import classify_events
from src.config import FUEL_COL as FUEL_COLUMN
from src.config import STATUS_COL as STATUS_COLUMN
from src.config import TIME_COL as TIMESTAMP_COLUMN
from src.preprocess import clean_fuel
from src.predict import (
    parse_status,
    predict_arrays,
    zero_bridged_losses_for,
)


class AnalysisError(Exception):
    """Erreur "propre" à afficher telle quelle dans l'interface."""


def _read_input(csv_path):
    if not os.path.exists(csv_path):
        raise AnalysisError(f"Fichier introuvable : {csv_path}")
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise AnalysisError(f"Impossible de lire le CSV : {exc}") from exc

    missing = [c for c in (FUEL_COLUMN, STATUS_COLUMN, TIMESTAMP_COLUMN)
               if c not in df.columns]
    if missing:
        raise AnalysisError(
            "Colonne(s) attendue(s) absente(s) de ce fichier :\n" + "\n".join(missing)
        )
    return df, clean_fuel(df[FUEL_COLUMN]), df[STATUS_COLUMN].to_numpy(), df[TIMESTAMP_COLUMN].to_numpy()


def _predict(csv_path, fuel, status):
    try:
        return predict_arrays(fuel, status)
    except FileNotFoundError as exc:
        raise AnalysisError(
            "Modèle introuvable (model/random_forest.pkl).\n"
            "Lancez d'abord `python utils/main.py` pour entraîner et sauvegarder le modèle."
        ) from exc
    except Exception as exc:
        raise AnalysisError(f"Erreur pendant l'analyse de {csv_path} : {exc}") from exc


def _build_result(csv_path, df, fuel, status, timestamps, prediction, events, events_ignored):
    return {
        "csv_path": csv_path,
        "filename": os.path.basename(csv_path),
        "fuel": fuel,
        "status": status,
        "active": parse_status(status, len(fuel)),
        "tank_capacity": read_tank_capacity(df),
        "timestamps": timestamps,
        "n_rows": len(fuel),
        "n_windows": int(len(prediction)),
        "n_alert_windows": int(prediction.sum()),
        "events": events,
        "n_events": len(events),
        "events_ignored": events_ignored,
        "n_events_ignored": len(events_ignored),
        "has_theft": len(events) > 0,
        "has_sensor_glitch": len(events_ignored) > 0,
        "has_issue": len(events) > 0 or len(events_ignored) > 0,
    }


def analyze_file(csv_path):
    """
    Lance la prédiction sur un fichier et retourne toutes les infos
    nécessaires à l'affichage (résumé + périodes + données du graphique).
    Lève AnalysisError avec un message clair en cas de problème (modèle
    manquant, colonnes absentes, fichier illisible, etc.).
    """
    df, fuel, status, timestamps = _read_input(csv_path)
    prediction = _predict(csv_path, fuel, status)

    glitch_mask = detect_sensor_glitches(fuel)
    # vols masqués par une chute à 0 : ne pas les reclasser en « Data incomplete »
    bridged = zero_bridged_losses_for(fuel, status)
    events, events_ignored = classify_events(
        prediction, glitch_mask, bridged, fuel, timestamps
    )
    return _build_result(
        csv_path, df, fuel, status, timestamps, prediction, events, events_ignored
    )
