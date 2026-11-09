import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

def _smooth(raw_pred, min_consecutive):
    """N'alerte qu'à partir de la `min_consecutive`-ième fenêtre positive consécutive."""
    raw_pred = np.asarray(raw_pred)
    out = np.zeros_like(raw_pred)
    if len(raw_pred) == 0:
        return out
    idx = np.arange(len(raw_pred))
    last_reset = np.maximum.accumulate(np.where(raw_pred == 1, -1, idx))
    out[(idx - last_reset) >= min_consecutive] = 1
    return out


def _window_counts(row_mask, window_size):
    """Nombre de lignes marquées dans chaque fenêtre [i, i+window_size-1]."""
    n_windows = max(0, len(row_mask) - window_size + 1)
    cs = np.concatenate(([0], np.cumsum(row_mask, dtype=np.int64)))
    return cs[window_size:window_size + n_windows] - cs[:n_windows]


def _rows_to_windows(row_mask, window_size):
    """Marque les fenêtres qui contiennent au moins une ligne marquée."""
    return _window_counts(row_mask, window_size) > 0


def _dilate(starts, length, n):
    """Masque de lignes : True sur [s, s+length-1] pour chaque s de `starts`."""
    marks = np.zeros(n + 1, dtype=np.int32)
    np.add.at(marks, starts, 1)
    np.add.at(marks, np.minimum(starts + length, n), -1)
    return np.cumsum(marks[:-1]) > 0


def _median_filter(fuel, window_size):
    """Supprime les pics alternés courts sans lisser une baisse durable."""
    if len(fuel) < window_size:
        return fuel.copy()
    radius = window_size // 2
    padded = np.pad(fuel, (radius, radius), mode="edge")
    return np.median(sliding_window_view(padded, window_size), axis=1)


