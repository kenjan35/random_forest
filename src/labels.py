import numpy as np


def create_labels(number_of_windows, window_size, theft_intervals):
    """
    Fenêtre i (lignes i .. i+window_size-1) = 1 si elle chevauche au moins
    une ligne d'un intervalle de vol [start, end] (bornes incluses).
    Version vectorisée : une fenêtre chevauche [s, e] ssi s-window_size+1 <= i <= e.
    """
    marks = np.zeros(number_of_windows + 1, dtype=np.int32)
    for theft_start, theft_end in theft_intervals:
        first = max(0, int(theft_start) - window_size + 1)
        last = min(number_of_windows - 1, int(theft_end))
        if first <= last:
            marks[first] += 1
            marks[last + 1] -= 1
    return (np.cumsum(marks[:-1]) > 0).astype(np.int8)
