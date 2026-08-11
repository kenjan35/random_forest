"""
Fait le pont entre le pipeline existant (src/predict.py) et l'interface
graphique : lance l'analyse d'un fichier, regroupe les fenêtres en alerte
en périodes lisibles, et prépare les données nécessaires au graphique.
"""

import os
import glob

import numpy as np
import pandas as pd

from src.predict import predict, WINDOW_SIZE

FUEL_COLUMN = "(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"
STATUS_COLUMN = "FSA Generator Running [MFSX:01:1:12] (S2)"
TIMESTAMP_COLUMN = "Time stamp"


class AnalysisError(Exception):
    """Erreur "propre" à afficher telle quelle dans l'interface."""


def group_consecutive(indices):
    """Regroupe une liste d'indices triés en intervalles consécutifs."""
    if len(indices) == 0:
        return []
    groups = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            groups.append((start, prev))
            start = prev = idx
    groups.append((start, prev))
    return groups


def find_csv_files(folder):
    return sorted(glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True))


# Fraction minimale d'une fenêtre d'alerte devant coïncider avec un
# décrochage capteur pour que l'alerte soit reclassée comme anomalie
# plutôt que comme vol suspecté.
GLITCH_OVERLAP_THRESHOLD = 0.6

# Une chute à 0 L n'est considérée comme un décrochage capteur que si le
# réservoir n'était PAS déjà proche de vide juste avant ou juste après
# (sinon il s'agit d'une vraie fin de réservoir, cf. panne sèche).
GLITCH_BASELINE_RATIO = 0.3


def detect_sensor_glitches(fuel, baseline_ratio=GLITCH_BASELINE_RATIO):
    """
    Détecte les décrochages capteur : le niveau de carburant tombe
    brutalement à 0 L puis remonte à un niveau proche de celui d'avant la
    coupure. C'est physiquement impossible pour une vraie fuite ou un vrai
    vol (le carburant ne "revient" pas tout seul dans le réservoir) : c'est
    la signature typique d'une coupure de communication ou d'une
    réinitialisation du capteur à 0.

    Ne touche pas à la logique de prédiction : c'est un filtre appliqué en
    plus, sur les données brutes, pour qualifier les alertes a posteriori.

    Retourne un tableau booléen (même taille que `fuel`), True pour les
    lignes appartenant à un épisode identifié comme décrochage capteur.
    """
    glitch = np.zeros(len(fuel), dtype=bool)
    if len(fuel) == 0:
        return glitch

    capacity_estimate = float(np.quantile(fuel, 0.95)) or 1.0
    threshold = baseline_ratio * capacity_estimate

    zero_indices = np.flatnonzero(fuel == 0).tolist()
    for start, end in group_consecutive(zero_indices):
        before = fuel[start - 1] if start > 0 else None
        after = fuel[end + 1] if end + 1 < len(fuel) else None
        was_full_before = before is not None and before >= threshold
        recovers_after = after is not None and after >= threshold
        if was_full_before or recovers_after:
            glitch[start:end + 1] = True

    return glitch


def analyze_file(csv_path):
    """
    Lance predict() sur un fichier et retourne toutes les infos nécessaires
    à l'affichage (résumé + détail des périodes + données pour le graphique).
    Lève AnalysisError avec un message clair en cas de problème (modèle
    manquant, colonnes absentes, fichier vide, etc.).
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

    try:
        prediction = predict(csv_path)
    except FileNotFoundError as exc:
        raise AnalysisError(
            "Modèle introuvable (model/random_forest.pkl).\n"
            "Lancez d'abord `python main.py` pour entraîner et sauvegarder le modèle."
        ) from exc
    except Exception as exc:
        raise AnalysisError(f"Erreur pendant l'analyse : {exc}") from exc

    fuel = df[FUEL_COLUMN].to_numpy(dtype=float)
    status = df[STATUS_COLUMN].to_numpy()
    timestamps = df[TIMESTAMP_COLUMN].to_numpy()
    active = np.array(["Active" in str(s) for s in status])

    alert_window_indices = [i for i, v in enumerate(prediction) if v == 1]
    window_events = group_consecutive(alert_window_indices)

    glitch_mask = detect_sensor_glitches(fuel)

    events = []
    events_ignored = []
    for (window_start, window_end) in window_events:
        row_start = window_start
        row_end = min(window_end + WINDOW_SIZE - 1, len(timestamps) - 1)
        span = glitch_mask[row_start:row_end + 1]
        glitch_ratio = float(span.mean()) if len(span) else 0.0

        event = {
            "row_start": int(row_start),
            "row_end": int(row_end),
            "ts_start": str(timestamps[row_start]),
            "ts_end": str(timestamps[row_end]),
            "glitch_ratio": round(glitch_ratio, 2),
        }

        # L'alerte coïncide surtout avec un décrochage capteur identifié :
        # on l'écarte du décompte de vols mais on la garde à part, visible,
        # plutôt que de la faire disparaître silencieusement.
        if glitch_ratio >= GLITCH_OVERLAP_THRESHOLD:
            events_ignored.append(event)
        else:
            events.append(event)

    return {
        "csv_path": csv_path,
        "filename": os.path.basename(csv_path),
        "fuel": fuel,
        "status": status,
        "active": active,
        "timestamps": timestamps,
        "n_rows": len(fuel),
        "n_windows": int(len(prediction)),
        "n_alert_windows": int(prediction.sum()) if len(prediction) else 0,
        "events": events,
        "n_events": len(events),
        "events_ignored": events_ignored,
        "n_events_ignored": len(events_ignored),
        "has_theft": len(events) > 0,
    }