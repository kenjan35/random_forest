import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from src.predict import RULE_RECOVERY_TOL, RULE_RECOVERY_WINDOW, RULE_WINDOW_SIZE, RULE_PERSISTENT_STEP_MIN_LOSS
from src.predict_generic_utils import _window_counts

def _persistent_step_loss_mask(fuel, dropout_mask, minimum_loss=RULE_PERSISTENT_STEP_MIN_LOSS):
    """Chutes brutales, précédées d'un niveau stable, qui restent au nouveau niveau."""
    n = len(fuel)
    mask = np.zeros(n, dtype=bool)
    if n < 24:  # il faut 20 relevés stables avant et 3 après
        return mask

    candidates = _persistent_candidates(fuel, dropout_mask, minimum_loss)
    for i, before, loss in candidates:
        tolerance = max(2.0, RULE_RECOVERY_TOL * loss)
        recovery_end = min(n, i + 1 + RULE_RECOVERY_WINDOW)
        if not np.any(np.abs(fuel[i + 3:recovery_end] - before) <= tolerance):
            mask[i:i + RULE_WINDOW_SIZE] = True
    return mask


def _persistent_candidates(fuel, dropout_mask, minimum_loss):
    idx = np.arange(20, len(fuel) - 3)
    stable = np.ptp(sliding_window_view(fuel, 20), axis=1)[idx - 20] <= 10.0
    median3 = np.median(sliding_window_view(fuel, 3), axis=1)
    before = median3[idx - 3]
    loss = before - median3[idx]
    no_dropout = _window_counts(dropout_mask, 4)[idx - 1] == 0
    return ((int(idx[k]), float(before[k]), float(loss[k]))
            for k in np.flatnonzero(stable & no_dropout & (loss > minimum_loss)))

