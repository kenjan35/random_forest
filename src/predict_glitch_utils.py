import numpy as np
from src.predict import GLITCH_REFERENCE_FRACTION

def find_zero_segments(fuel, include_leading=False):
    """
    Segments (start, end) de relevés consécutifs à exactement 0.
    Par défaut, un segment qui commence à la ligne 0 est ignoré (pas de
    niveau "avant" auquel le comparer).
    """
    is_zero = np.concatenate(([0], (np.asarray(fuel) == 0).astype(np.int8), [0]))
    edges = np.diff(is_zero)
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1) - 1
    if not include_leading:
        keep = starts > 0
        starts, ends = starts[keep], ends[keep]
    return list(zip(starts.tolist(), ends.tolist()))


def _find_dropout_segments(fuel):
    return find_zero_segments(fuel, include_leading=False)


def _segments_mask(segments, n):
    mask = np.zeros(n, dtype=bool)
    for start, end in segments:
        mask[start:end + 1] = True
    return mask


def _confirmed_glitch_segments(fuel, segments):
    """Coupures dont le niveau juste avant OU juste après est un niveau réel."""
    if len(fuel) == 0:
        return []
    reference = float(np.quantile(fuel, 0.95)) or 1.0
    threshold = GLITCH_REFERENCE_FRACTION * reference
    n = len(fuel)
    confirmed = []
    for start, end in segments:
        before = fuel[start - 1] if start > 0 else 0.0
        after = fuel[end + 1] if end + 1 < n else 0.0
        if before >= threshold or after >= threshold:
            confirmed.append((start, end))
    return confirmed


def confirmed_glitch_mask(fuel, include_leading=False):
    """
    Masque (par ligne) des coupures capteur confirmées : relevés à 0 dont le
    niveau juste avant ou juste après est un niveau réel (>= 30% du P95).
    Utilisé aussi par l'interface pour classer les alertes en "Data incomplete".
    """
    fuel = np.asarray(fuel, dtype=float)
    segments = find_zero_segments(fuel, include_leading)
    return _segments_mask(_confirmed_glitch_segments(fuel, segments), len(fuel))
