import numpy as np
from src.predict import RULE_OSCILLATION_STEP, RULE_MAX_SIGN_CHANGES, RULE_MIN_LOSS, RULE_OPPOSITE_RETURN_TOL, RULE_FILTER_WINDOW, RULE_WINDOW_SIZE, RULE_RECOVERY_TOL, RULE_RECOVERY_WINDOW, RULE_OSCILLATION_LOOKAHEAD
from src.predict_generic_utils import _median_filter, _window_counts

def _is_oscillating_window(fuel):
    """Succession de hausses et baisses fortes de la jauge."""
    delta = np.diff(fuel)
    significant = delta[np.abs(delta) >= RULE_OSCILLATION_STEP]
    if len(significant) < RULE_MAX_SIGN_CHANGES + 1:
        return False
    return np.sum(significant[1:] * significant[:-1] < 0) >= RULE_MAX_SIGN_CHANGES


def _has_opposite_excursion(fuel, loss):
    """Pic (ou creux) important qui revient avant la fin de la fenêtre."""
    if len(fuel) < 3 or loss <= RULE_MIN_LOSS:
        return False
    if abs(fuel[-1] - fuel[0]) > RULE_OPPOSITE_RETURN_TOL:
        return False
    last = len(fuel) - 1
    peak = int(np.argmax(fuel))
    if 0 < peak < last and fuel[peak] - fuel[0] > RULE_MIN_LOSS and fuel[peak] - fuel[-1] > RULE_MIN_LOSS:
        return True
    trough = int(np.argmin(fuel))
    return 0 < trough < last and fuel[0] - fuel[trough] > RULE_MIN_LOSS and fuel[-1] - fuel[trough] > RULE_MIN_LOSS


def _rule_based_flags(fuel, dropout_mask):
    """
    Signale (par ligne) une perte nette de plus de RULE_MIN_LOSS litres sur
    RULE_WINDOW_SIZE relevés, quel que soit l'état du générateur, si le
    niveau ne revient pas près du niveau de départ dans les 24 h suivantes.
    Fenêtre glissante : détecte aussi les pertes progressives.
    """
    n = len(fuel)
    flags = np.zeros(n, dtype=np.int8)
    if n < RULE_WINDOW_SIZE:
        return flags

    filtered = _median_filter(fuel, RULE_FILTER_WINDOW)
    starts = np.arange(n - RULE_WINDOW_SIZE + 1)
    ends = starts + RULE_WINDOW_SIZE - 1
    loss = filtered[starts] - filtered[ends]
    candidates = (loss > RULE_MIN_LOSS) & (_window_counts(dropout_mask, RULE_WINDOW_SIZE) == 0)
    for start in np.flatnonzero(candidates):
        if _is_rule_candidate(fuel, filtered, dropout_mask, int(start), float(loss[start])):
            end = start + RULE_WINDOW_SIZE - 1
            flags[start:end + 1] = 1

    return flags


def _is_rule_candidate(fuel, filtered, dropout_mask, start, window_loss):
    end = start + RULE_WINDOW_SIZE - 1
    if _is_oscillating_window(fuel[start:end + 1]):
        return False
    lo = max(0, start - RULE_OSCILLATION_LOOKAHEAD)
    hi = min(len(fuel), end + 1 + RULE_OSCILLATION_LOOKAHEAD)
    if _has_opposite_excursion(fuel[lo:hi], window_loss):
        return False
    tolerance = max(2.0, RULE_RECOVERY_TOL * window_loss)
    recovery_end = min(len(fuel), end + 1 + RULE_RECOVERY_WINDOW)
    recovered = np.any(~dropout_mask[end + 1:recovery_end]
                       & (np.abs(filtered[end + 1:recovery_end] - filtered[start]) <= tolerance))
    return not recovered
