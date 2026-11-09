import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from src.predict import _CHUNK, RULE_LOCAL_OSCILLATION_WINDOW, RULE_LOCAL_OSCILLATION_AMPLITUDE, RULE_LOCAL_OSCILLATION_RETURN_TOL
from src.predict_generic_utils import _dilate

def _local_returning_excursion_mask(fuel):
    """Lignes appartenant à une excursion locale forte qui revient à son niveau initial."""
    n = len(fuel)
    window = RULE_LOCAL_OSCILLATION_WINDOW
    amplitude_min = RULE_LOCAL_OSCILLATION_AMPLITUDE
    if n < window:
        return np.zeros(n, dtype=bool)

    all_segments = sliding_window_view(fuel, window)
    return _find_excursion_starts(all_segments, window, n, amplitude_min)


def _find_excursion_starts(all_segments, window, n, amplitude_min):
    hit_starts = []
    for offset in range(0, len(all_segments), _CHUNK):
        seg = all_segments[offset:offset + _CHUNK]
        before = np.median(seg[:, :8], axis=1)
        after = np.median(seg[:, -8:], axis=1)
        amplitude = seg.max(axis=1) - seg.min(axis=1)
        high = (seg >= (before + amplitude_min)[:, None]).sum(axis=1)
        low = (seg <= (before - amplitude_min)[:, None]).sum(axis=1)
        hit = (
            (amplitude >= amplitude_min)
            & (np.abs(after - before) <= RULE_LOCAL_OSCILLATION_RETURN_TOL)
            & ((high >= 3) | (low >= 3))
        )
        hit_starts.append(np.flatnonzero(hit) + offset)

    return _dilate(np.concatenate(hit_starts), window, n)
