import numpy as np
from src.predict import WINDOW_SIZE, RULE_MIN_LOSS
from src.predict_generic_utils import _rows_to_windows
from src.predict_excursion_utils import _local_returning_excursion_mask
from src.predict_persistent_utils import _persistent_step_loss_mask
from src.predict_bridge_utils import zero_bridged_losses

def _combine_predictions(fuel, dropout_mask, glitch_windows, ml_pred, rule_pred):
    final = np.maximum(ml_pred, rule_pred)
    final[glitch_windows] = 0
    local = _rows_to_windows(_local_returning_excursion_mask(fuel), WINDOW_SIZE)
    final[local] = 0
    persistent = _rows_to_windows(
        _persistent_step_loss_mask(fuel, dropout_mask, minimum_loss=RULE_MIN_LOSS), WINDOW_SIZE
    )
    final[persistent] = np.maximum(final[persistent], rule_pred[persistent])
    return final


def _apply_bridged_losses(prediction, fuel, active, reliable, active_scale):
    bridged_rows = np.zeros(len(fuel), dtype=bool)
    for loss in zero_bridged_losses(fuel, active, reliable, active_scale):
        bridged_rows[max(0, loss["start"] - 1):min(len(fuel), loss["end"] + 2)] = True
    if bridged_rows.any():
        prediction[_rows_to_windows(bridged_rows, WINDOW_SIZE)] = 1
    return prediction
