"""
Calculs sur le niveau de carburant partagés par l'analyse, le graphique et les
rapports (sans dépendance Qt).
"""

import numpy as np


def drop_extremes(fuel, row_start, row_end):
    """
    Niveau haut et niveau bas d'une descente de carburant dans [row_start, row_end] :
    le point le plus bas, et le point le plus haut qui le PRÉCÈDE (un ravitaillement
    après la chute ne doit pas être pris pour le niveau de départ). Les relevés à 0
    (coupure capteur) sont ignorés dès qu'il existe de vrais niveaux.
    Retourne ((index_haut, litres_haut), (index_bas, litres_bas)) ou None s'il n'y
    a aucune baisse.
    """
    n = len(fuel)
    row_start, row_end = max(0, int(row_start)), min(n - 1, int(row_end))
    if row_end <= row_start:
        return None
    segment = np.asarray(fuel[row_start:row_end + 1], dtype=float)
    valid = segment > 0
    if not valid.any():
        return None
    i_low = int(np.argmin(np.where(valid, segment, np.inf)))
    i_high = int(np.argmax(np.where(valid[:i_low + 1], segment[:i_low + 1], -np.inf)))
    if segment[i_high] <= segment[i_low]:
        return None
    return ((row_start + i_high, float(segment[i_high])), (row_start + i_low, float(segment[i_low])))


def event_loss(fuel, row_start, row_end):
    """Litres perdus sur une période : niveau haut − niveau bas (jamais négatif)."""
    extremes = drop_extremes(fuel, row_start, row_end)
    if extremes is None:
        return 0.0
    (_ih, high), (_il, low) = extremes
    return round(high - low, 1)
