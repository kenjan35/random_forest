import numpy as np
from src.predict import MIN_SCALE_FLOOR, SCALE_PERCENTILE_HIGH, SCALE_PERCENTILE_LOW, MIN_SAMPLES_FOR_HIGH_PERCENTILE

def _robust_scale(values):
    """
    Percentile adapté au nombre d'échantillons :
      - peu (< MIN_SAMPLES_FOR_HIGH_PERCENTILE) -> SCALE_PERCENTILE_LOW (90e) :
        une seule anomalie extrême ne doit pas définir sa propre échelle ;
      - beaucoup -> SCALE_PERCENTILE_HIGH (97e) : couvre les sites dont le
        bruit de mesure est naturellement plus fort.
    """
    if len(values) == 0:
        return MIN_SCALE_FLOOR
    pct = SCALE_PERCENTILE_HIGH if len(values) >= MIN_SAMPLES_FOR_HIGH_PERCENTILE else SCALE_PERCENTILE_LOW
    return max(float(np.percentile(values, pct)), MIN_SCALE_FLOOR)


def _site_scales(fuel, active, status_reliable, dropout_mask):
    delta = np.diff(fuel, prepend=fuel[:1]) if len(fuel) else fuel.copy()

    # une transition qui touche une coupure (ex : 89 -> 0 ou 0 -> 87) ne doit
    # pas polluer le calcul du bruit "normal"
    previous_is_dropout = np.concatenate(([False], dropout_mask[:-1]))
    valid = ~(dropout_mask | previous_is_dropout)

    if status_reliable:
        noise_scale = _robust_scale(np.abs(delta[~active & valid]))
        consumption = -delta[active & valid]
        active_scale = _robust_scale(consumption[consumption > 0])
    else:
        # Mode dégradé : statut non informatif -> une échelle unique calibrée
        # sur toutes les baisses observées.
        consumption = -delta[valid]
        noise_scale = active_scale = _robust_scale(consumption[consumption > 0])

    return noise_scale, active_scale


