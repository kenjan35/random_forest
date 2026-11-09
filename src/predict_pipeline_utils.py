import numpy as np
from src.features import create_features
from src.windows import create_windows
from src.predict import WINDOW_SIZE, MIN_CONSECUTIVE, GATE_LOSS_MULTIPLIER
from src.preprocess import load_site
from src.predict_model_utils import load_model
from src.predict_status_utils import parse_status, _status_is_reliable
from src.predict_glitch_utils import _find_dropout_segments, _segments_mask, _confirmed_glitch_segments
from src.predict_scale_utils import _site_scales
from src.predict_generic_utils import _rows_to_windows, _window_counts, _smooth
from src.predict_rule_utils import _rule_based_flags
from src.predict_combine_utils import _combine_predictions
from src.predict_combine_utils import _apply_bridged_losses

def _magnitude_gate(X, active, noise_scale, active_scale, status_reliable):
    """Ne garde une alerte ML que si la perte de la fenêtre dépasse nettement la perte attendue."""
    n = X.shape[0]
    if status_reliable:
        n_active = _window_counts(active, WINDOW_SIZE)[:n]
        expected_ceiling = n_active * active_scale + (WINDOW_SIZE - n_active) * noise_scale
    else:
        expected_ceiling = np.full(n, WINDOW_SIZE * noise_scale)
    return X[:, 1] < -(GATE_LOSS_MULTIPLIER * expected_ceiling)


def predict(csv_path):
    """Retourne un tableau 0/1 par fenêtre de WINDOW_SIZE lignes (fenêtre i = lignes i..i+19)."""
    load_model()  # échoue tôt (FileNotFoundError) si le modèle est absent
    fuel, status, _ = load_site(csv_path)
    return predict_arrays(fuel, status)


def predict_arrays(fuel, status=None):
    """
    Même chose que predict(), à partir de données déjà chargées : évite de
    relire le CSV quand l'appelant l'a déjà ouvert (interface graphique).
    `fuel` doit être nettoyé (voir src.preprocess.clean_fuel).
    """
    model, threshold = load_model()

    fuel = np.asarray(fuel, dtype=float)
    n = len(fuel)
    n_windows = max(0, n - WINDOW_SIZE + 1)
    if n_windows == 0:
        return np.zeros(0, dtype=np.int64)
    active, reliable, dropout_mask, glitches, glitch_windows, noise, scale = _prediction_context(
        fuel, status
    )
    ml_pred, rule_pred = _predict_components(
        fuel, active, reliable, dropout_mask, glitch_windows, noise, scale, model, threshold
    )
    final_pred = _combine_predictions(fuel, dropout_mask, glitch_windows, ml_pred, rule_pred)
    if len(glitches) >= 2:
        final_pred[:] = 0
    return _apply_bridged_losses(final_pred, fuel, active, reliable, scale)


def _prediction_context(fuel, status):
    n = len(fuel)
    active = parse_status(status, n)
    reliable = _status_is_reliable(active)
    dropout = _find_dropout_segments(fuel)
    dropout_mask = _segments_mask(dropout, n)
    glitches = _confirmed_glitch_segments(fuel, dropout)
    glitch_windows = _rows_to_windows(_segments_mask(glitches, n), WINDOW_SIZE)
    noise, scale = _site_scales(fuel, active, reliable, dropout_mask)
    return active, reliable, dropout_mask, glitches, glitch_windows, noise, scale


def _predict_components(fuel, active, reliable, dropout_mask, glitch_windows,
                        noise, scale, model, threshold):
    X = create_windows(create_features(fuel), WINDOW_SIZE)
    proba = model.predict_proba(X)[:, 1]
    raw = (proba >= threshold) & _magnitude_gate(X, active, noise, scale, reliable)
    raw[glitch_windows] = False
    ml_pred = _smooth(raw.astype(np.int64), MIN_CONSECUTIVE)
    rule_pred = _rows_to_windows(_rule_based_flags(fuel, dropout_mask), WINDOW_SIZE).astype(np.int8)
    return ml_pred, rule_pred
