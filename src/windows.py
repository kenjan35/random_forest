import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def create_windows(features, window_size) -> np.ndarray:
    """
    features: array (N, F) avec au minimum colonne 0 = fuel, colonne 1 = delta.
    Si features.py fournit au moins 4 colonnes (delta relatif en colonne 3),
    il est aussi utilisé.

    Retourne, pour chaque fenêtre, un vecteur de statistiques agrégées
    (niveau de départ, variation totale, moyenne/écart-type/min/max du
    delta, amplitude cumulée, pente, [delta relatif cumulé]).
    L'ordre des colonnes doit rester identique : le modèle entraîné en dépend.
    """
    fuel = features[:, 0]
    delta = features[:, 1]
    has_rel = features.shape[1] >= 4
    n = len(fuel) - window_size + 1
    if n <= 0:
        return np.zeros((0, 9 if has_rel else 8))

    fuel_windows = sliding_window_view(fuel, window_size)
    delta_windows = sliding_window_view(delta, window_size)

    fuel_start = fuel_windows[:, 0]
    total_variation = fuel_windows[:, -1] - fuel_start

    xc = np.arange(window_size, dtype=float)
    xc -= xc.mean()
    slope = (fuel_windows @ xc) / (xc ** 2).sum()

    cols = [
        fuel_start,
        total_variation,
        delta_windows.mean(axis=1),
        delta_windows.std(axis=1),
        delta_windows.min(axis=1),
        delta_windows.max(axis=1),
        np.abs(delta_windows).sum(axis=1),
        slope,
    ]
    if has_rel:
        cols.append(sliding_window_view(features[:, 3], window_size).sum(axis=1))

    return np.column_stack(cols)
