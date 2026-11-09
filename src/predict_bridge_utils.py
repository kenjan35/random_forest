import numpy as np
from src.predict import ZERO_BRIDGE_BEFORE_ROWS, ZERO_BRIDGE_AFTER_ROWS, ZERO_BRIDGE_MAX_GAP_UNRELIABLE, ZERO_BRIDGE_STABLE_TOL, GATE_LOSS_MULTIPLIER, RULE_MIN_LOSS
from src.predict_status_utils import parse_status, _status_is_reliable
from src.predict_glitch_utils import _find_dropout_segments, _segments_mask
from src.predict_scale_utils import _site_scales

def zero_bridged_losses(fuel, active, status_reliable, active_scale):
    """
    Vols cachés derrière une chute à 0 : le niveau passe de A à 0 puis revient
    à un niveau B nettement plus bas, et y reste. Une vraie coupure capteur
    revient au niveau d'avant ; un ravitaillement revient plus haut — ces deux
    cas ne sont pas concernés.
    Retourne [{"start", "end", "before", "after", "loss"}, ...] (lignes à 0 incluses).
    """
    fuel = np.asarray(fuel, dtype=float)
    losses = []
    for start, end in _find_dropout_segments(fuel):
        loss = _zero_bridge_loss(fuel, active, status_reliable, active_scale, start, end)
        if loss is not None:
            losses.append(loss)
    return losses


def _zero_bridge_loss(fuel, active, status_reliable, active_scale, start, end):
    before_vals = fuel[max(0, start - ZERO_BRIDGE_BEFORE_ROWS):start]
    after_vals = fuel[end + 1:end + 1 + ZERO_BRIDGE_AFTER_ROWS]
    if len(before_vals) < 3 or len(after_vals) < ZERO_BRIDGE_AFTER_ROWS:
        return None
    if np.any(before_vals <= 0) or np.any(after_vals <= 0):
        return None
    if not status_reliable and end - start + 1 > ZERO_BRIDGE_MAX_GAP_UNRELIABLE:
        return None
    before, after = float(np.median(before_vals)), float(np.median(after_vals))
    loss = before - after
    n_active = int(active[start:end + 1].sum()) if status_reliable else 0
    expected = GATE_LOSS_MULTIPLIER * n_active * active_scale
    if loss <= max(RULE_MIN_LOSS, expected):
        return None
    if np.ptp(after_vals) > max(ZERO_BRIDGE_STABLE_TOL, 0.2 * loss):
        return None
    return {"start": int(start), "end": int(end), "before": round(before, 1),
            "after": round(after, 1), "loss": round(loss, 1)}


def zero_bridged_losses_for(fuel, status=None):
    """Version autonome (pour l'interface) : calcule statut et échelles puis détecte."""
    fuel = np.asarray(fuel, dtype=float)
    if len(fuel) == 0:
        return []
    active = parse_status(status, len(fuel))
    reliable = _status_is_reliable(active)
    dropout_mask = _segments_mask(_find_dropout_segments(fuel), len(fuel))
    _, active_scale = _site_scales(fuel, active, reliable, dropout_mask)
    return zero_bridged_losses(fuel, active, reliable, active_scale)
