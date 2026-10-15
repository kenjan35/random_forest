import numpy as np


def compute_delta(fuel):
    """Variation entre deux relevés consécutifs (0 pour le premier)."""
    fuel = np.asarray(fuel, dtype=float)
    if len(fuel) == 0:
        return fuel.copy()
    return np.diff(fuel, prepend=fuel[0])


def create_features(fuel):
    """
    Colonnes : fuel, delta, |delta|, delta relatif, |delta relatif|.
    L'ordre doit rester identique : le modèle entraîné en dépend.
    """
    fuel = np.asarray(fuel, dtype=float)
    delta = compute_delta(fuel)
    rel_delta = np.divide(delta, fuel, out=np.zeros_like(delta), where=fuel != 0)
    return np.column_stack((fuel, delta, np.abs(delta), rel_delta, np.abs(rel_delta)))
