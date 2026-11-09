import numpy as np
import pandas as pd
from src.predict import MIN_STATE_ROWS

def _is_active_value(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False  # statut manquant : on ne le compte pas comme "en marche"
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return value != 0
    text = str(value).strip().casefold()
    if text in {"0", "false", "inactive", "off", "stopped"} or "inactive" in text:
        return False
    return text in {"1", "true", "active", "on", "running"} or "active" in text


def parse_status(status, n_rows):
    """Convertit la colonne de statut en booléens (une seule évaluation par valeur distincte)."""
    if status is None:
        return np.zeros(n_rows, dtype=bool)
    series = pd.Series(status)
    mapping = {v: _is_active_value(v) for v in series.dropna().unique()}
    return series.map(mapping).fillna(False).to_numpy(dtype=bool)


def _status_is_reliable(active):
    """
    Le statut Actif/Inactif n'est exploité que si les DEUX états ont été
    observés un nombre suffisant de fois (en nombre absolu de lignes : un
    groupe de secours peut légitimement n'être actif que 2-3% du temps).
    """
    n_active = int(active.sum())
    return n_active >= MIN_STATE_ROWS and (len(active) - n_active) >= MIN_STATE_ROWS


