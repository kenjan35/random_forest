import os
from functools import lru_cache

import numpy as np
import joblib
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

from src.config import MODEL_PATH, THRESHOLD_PATH, DEFAULT_THRESHOLD, WINDOW_SIZE
from src.preprocess import load_site
from src.features import create_features
from src.windows import create_windows

MIN_CONSECUTIVE = 3

RULE_WINDOW_SIZE = 12
RULE_MIN_LOSS = 15.0
RULE_RECOVERY_WINDOW = 288   # 24 h à raison d'une mesure toutes les 5 minutes
RULE_RECOVERY_TOL = 0.3
RULE_FILTER_WINDOW = 13      # ~1 h pour neutraliser les plateaux parasites courts
RULE_OSCILLATION_STEP = 1.0
RULE_MAX_SIGN_CHANGES = 3
RULE_OSCILLATION_LOOKAHEAD = 6
RULE_LOCAL_OSCILLATION_WINDOW = 60
RULE_LOCAL_OSCILLATION_AMPLITUDE = 30.0
RULE_LOCAL_OSCILLATION_RETURN_TOL = 10.0
RULE_OPPOSITE_RETURN_TOL = 10.0
RULE_PERSISTENT_STEP_MIN_LOSS = 50.0
GATE_LOSS_MULTIPLIER = 2.5
MIN_SCALE_FLOOR = 1.0
MIN_STATE_ROWS = 10           # nb minimal de lignes dans CHAQUE état pour juger le statut exploitable
SCALE_PERCENTILE_LOW = 90     # peu d'échantillons : limite la contamination par l'anomalie elle-même
SCALE_PERCENTILE_HIGH = 97    # beaucoup d'échantillons : tolère les sites naturellement bruyants
MIN_SAMPLES_FOR_HIGH_PERCENTILE = 100
GLITCH_REFERENCE_FRACTION = 0.3  # une coupure est confirmée si le niveau voisin dépasse 30% du P95

# Constantes conservées pour compatibilité (plus utilisées par la logique actuelle)
RULE_DROP_MULTIPLIER = 5
RULE_FILE_OSCILLATION_DEVIATION = 15.0
RULE_FILE_OSCILLATION_BASELINE_TOL = 10.0

_CHUNK = 50_000  # taille de bloc pour les calculs vectorisés gourmands en mémoire


# ---------------------------------------------------------------------------
# Chargement du modèle (mis en cache, rechargé automatiquement si le .pkl change)
# ---------------------------------------------------------------------------

def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


@lru_cache(maxsize=1)
def _load_model_cached(model_mtime, threshold_mtime):
    model = joblib.load(MODEL_PATH)
    threshold = float(joblib.load(THRESHOLD_PATH)) if threshold_mtime is not None else DEFAULT_THRESHOLD
    return model, threshold


def load_model():
    """Retourne (modèle, seuil). Le disque n'est relu que si les fichiers ont changé."""
    model_mtime = _mtime(MODEL_PATH)
    if model_mtime is None:
        raise FileNotFoundError(f"Modèle introuvable : {MODEL_PATH}")
    return _load_model_cached(model_mtime, _mtime(THRESHOLD_PATH))


# ---------------------------------------------------------------------------
# Outils génériques
# ---------------------------------------------------------------------------

def _smooth(raw_pred, min_consecutive):
    """N'alerte qu'à partir de la `min_consecutive`-ième fenêtre positive consécutive."""
    raw_pred = np.asarray(raw_pred)
    out = np.zeros_like(raw_pred)
    if len(raw_pred) == 0:
        return out
    idx = np.arange(len(raw_pred))
    last_reset = np.maximum.accumulate(np.where(raw_pred == 1, -1, idx))
    out[(idx - last_reset) >= min_consecutive] = 1
    return out


def _window_counts(row_mask, window_size):
    """Nombre de lignes marquées dans chaque fenêtre [i, i+window_size-1]."""
    n_windows = max(0, len(row_mask) - window_size + 1)
    cs = np.concatenate(([0], np.cumsum(row_mask, dtype=np.int64)))
    return cs[window_size:window_size + n_windows] - cs[:n_windows]


def _rows_to_windows(row_mask, window_size):
    """Marque les fenêtres qui contiennent au moins une ligne marquée."""
    return _window_counts(row_mask, window_size) > 0


# Alias de l'ancien nom (au cas où il serait importé ailleurs)
_glitch_window_mask = _rows_to_windows


def _dilate(starts, length, n):
    """Masque de lignes : True sur [s, s+length-1] pour chaque s de `starts`."""
    marks = np.zeros(n + 1, dtype=np.int32)
    np.add.at(marks, starts, 1)
    np.add.at(marks, np.minimum(starts + length, n), -1)
    return np.cumsum(marks[:-1]) > 0


def _median_filter(fuel, window_size):
    """Supprime les pics alternés courts sans lisser une baisse durable."""
    if len(fuel) < window_size:
        return fuel.copy()
    radius = window_size // 2
    padded = np.pad(fuel, (radius, radius), mode="edge")
    return np.median(sliding_window_view(padded, window_size), axis=1)


# ---------------------------------------------------------------------------
# Statut du générateur
# ---------------------------------------------------------------------------

def _is_active_value(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return False  # statut manquant : on ne le compte pas comme "en marche"
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return value != 0
    text = str(value).strip().casefold()
    if text in {"0", "false", "inactive", "off", "stopped"} or "inactive" in text:
        return False
    return text in {"1", "true", "active", "on", "running"} or "active" in text


def parse_status(status, n_rows):
    """Convertit la colonne de statut en booléens (une seule évaluation par valeur distincte)."""
    if status is None:
        return np.zeros(n_rows, dtype=bool)
    series = pd.Series(status)
    mapping = {v: _is_active_value(v) for v in series.dropna().unique()}
    return series.map(mapping).fillna(False).to_numpy(dtype=bool)


def _status_is_reliable(active):
    """
    Le statut Actif/Inactif n'est exploité que si les DEUX états ont été
    observés un nombre suffisant de fois (en nombre absolu de lignes : un
    groupe de secours peut légitimement n'être actif que 2-3% du temps).
    """
    n_active = int(active.sum())
    return n_active >= MIN_STATE_ROWS and (len(active) - n_active) >= MIN_STATE_ROWS


# ---------------------------------------------------------------------------
# Coupures capteur (relevés figés à 0)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Échelles de bruit / consommation propres au site
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Masques de suppression / confirmation
# ---------------------------------------------------------------------------

def _local_returning_excursion_mask(fuel):
    """Lignes appartenant à une excursion locale forte qui revient à son niveau initial."""
    n = len(fuel)
    window = RULE_LOCAL_OSCILLATION_WINDOW
    amplitude_min = RULE_LOCAL_OSCILLATION_AMPLITUDE
    if n < window:
        return np.zeros(n, dtype=bool)

    all_segments = sliding_window_view(fuel, window)
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


def _persistent_step_loss_mask(fuel, dropout_mask, minimum_loss=RULE_PERSISTENT_STEP_MIN_LOSS):
    """Chutes brutales, précédées d'un niveau stable, qui restent au nouveau niveau."""
    n = len(fuel)
    mask = np.zeros(n, dtype=bool)
    if n < 24:  # il faut 20 relevés stables avant et 3 après
        return mask

    idx = np.arange(20, n - 3)                                    # indices candidats
    stable = np.ptp(sliding_window_view(fuel, 20), axis=1)[idx - 20] <= 10.0
    median3 = np.median(sliding_window_view(fuel, 3), axis=1)     # median3[j] = médiane de fuel[j:j+3]
    before = median3[idx - 3]
    loss = before - median3[idx]
    no_dropout = _window_counts(dropout_mask, 4)[idx - 1] == 0    # lignes idx-1 .. idx+2

    for k in np.flatnonzero(stable & no_dropout & (loss > minimum_loss)):
        i = idx[k]
        tolerance = max(2.0, RULE_RECOVERY_TOL * loss[k])
        recovery_end = min(n, i + 1 + RULE_RECOVERY_WINDOW)
        if not np.any(np.abs(fuel[i + 3:recovery_end] - before[k]) <= tolerance):
            mask[i:i + RULE_WINDOW_SIZE] = True
    return mask


# ---------------------------------------------------------------------------
# Règle principale
# ---------------------------------------------------------------------------

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

    # filtres vectorisés les moins coûteux d'abord ; les tests restants ne
    # sont évalués que sur les rares fenêtres candidates
    candidates = (loss > RULE_MIN_LOSS) & (_window_counts(dropout_mask, RULE_WINDOW_SIZE) == 0)

    for start in np.flatnonzero(candidates):
        end = start + RULE_WINDOW_SIZE - 1
        if _is_oscillating_window(fuel[start:end + 1]):
            continue
        window_loss = loss[start]
        lo = max(0, start - RULE_OSCILLATION_LOOKAHEAD)
        hi = min(n, end + 1 + RULE_OSCILLATION_LOOKAHEAD)
        if _has_opposite_excursion(fuel[lo:hi], window_loss):
            continue

        tolerance = max(2.0, RULE_RECOVERY_TOL * window_loss)
        recovery_end = min(n, end + 1 + RULE_RECOVERY_WINDOW)
        recovered = np.any(
            ~dropout_mask[end + 1:recovery_end]
            & (np.abs(filtered[end + 1:recovery_end] - filtered[start]) <= tolerance)
        )
        if not recovered:
            flags[start:end + 1] = 1

    return flags


def _magnitude_gate(X, active, noise_scale, active_scale, status_reliable):
    """Ne garde une alerte ML que si la perte de la fenêtre dépasse nettement la perte attendue."""
    n = X.shape[0]
    if status_reliable:
        n_active = _window_counts(active, WINDOW_SIZE)[:n]
        expected_ceiling = n_active * active_scale + (WINDOW_SIZE - n_active) * noise_scale
    else:
        expected_ceiling = np.full(n, WINDOW_SIZE * noise_scale)
    return X[:, 1] < -(GATE_LOSS_MULTIPLIER * expected_ceiling)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

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

    active = parse_status(status, n)
    status_reliable = _status_is_reliable(active)

    dropout_segments = _find_dropout_segments(fuel)
    dropout_mask = _segments_mask(dropout_segments, n)
    confirmed_glitches = _confirmed_glitch_segments(fuel, dropout_segments)
    glitch_windows = _rows_to_windows(_segments_mask(confirmed_glitches, n), WINDOW_SIZE)

    noise_scale, active_scale = _site_scales(fuel, active, status_reliable, dropout_mask)

    # --- modèle ML (par fenêtre) ---
    X = create_windows(create_features(fuel), WINDOW_SIZE)
    proba = model.predict_proba(X)[:, 1]
    ml_raw = (proba >= threshold) & _magnitude_gate(X, active, noise_scale, active_scale, status_reliable)
    ml_raw[glitch_windows] = False
    ml_pred = _smooth(ml_raw.astype(np.int64), MIN_CONSECUTIVE)

    # --- règle (par ligne) convertie en fenêtres ---
    rule_pred = _rows_to_windows(_rule_based_flags(fuel, dropout_mask), WINDOW_SIZE).astype(np.int8)

    final_pred = np.maximum(ml_pred, rule_pred)
    final_pred[glitch_windows] = 0
    final_pred[_rows_to_windows(_local_returning_excursion_mask(fuel), WINDOW_SIZE)] = 0

    # une chute persistante confirmée par la règle reste signalée malgré les suppressions
    persistent = _rows_to_windows(
        _persistent_step_loss_mask(fuel, dropout_mask, minimum_loss=RULE_MIN_LOSS), WINDOW_SIZE
    )
    final_pred[persistent] = np.maximum(final_pred[persistent], rule_pred[persistent])

    if len(confirmed_glitches) >= 2:
        final_pred[:] = 0
    return final_pred
