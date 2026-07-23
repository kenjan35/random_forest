# import numpy as np

# def create_windows(dataframe, window_size) -> np.ndarray:
#     windows = []
#     for i in range(len(dataframe) - window_size + 1):
#         windows.append(dataframe[i:i + window_size])
#     return np.array(windows)

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def create_windows(features, window_size) -> np.ndarray:
    """
    features: array (N, F) avec au minimum colonne 0 = fuel, colonne 1 = delta.
    Si features.py fournit 5 colonnes (avec delta relatif en colonne 3), il
    est aussi utilisé.

    Retourne, pour chaque fenêtre, un vecteur de statistiques agrégées
    (niveau de départ, variation totale, moyenne/écart-type/min/max du
    delta, amplitude cumulée, pente) plutôt que la séquence brute -- signal
    beaucoup plus fort pour un Random Forest, et calcul entièrement
    vectorisé (rapide même sur des millions de lignes).
    """
    fuel = features[:, 0]
    delta = features[:, 1]
    has_rel = features.shape[1] >= 4
    n = len(fuel) - window_size + 1
    n_cols = 9 if has_rel else 8
    if n <= 0:
        return np.zeros((0, n_cols))

    fuel_windows = sliding_window_view(fuel, window_size)
    delta_windows = sliding_window_view(delta, window_size)

    fuel_start = fuel_windows[:, 0]
    total_variation = fuel_windows[:, -1] - fuel_start

    mean_delta = delta_windows.mean(axis=1)
    std_delta = delta_windows.std(axis=1)
    min_delta = delta_windows.min(axis=1)
    max_delta = delta_windows.max(axis=1)
    abs_cum = np.abs(delta_windows).sum(axis=1)

    x = np.arange(window_size, dtype=float)
    xc = x - x.mean()
    denom = (xc ** 2).sum()
    slope = (fuel_windows @ xc) / denom

    cols = [fuel_start, total_variation, mean_delta, std_delta,
            min_delta, max_delta, abs_cum, slope]

    if has_rel:
        rel_delta = features[:, 3]
        rel_windows = sliding_window_view(rel_delta, window_size)
        rel_cum = rel_windows.sum(axis=1)
        cols.append(rel_cum)

    return np.column_stack(cols)