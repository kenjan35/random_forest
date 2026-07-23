# import joblib

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows

# WINDOW_SIZE = 20

# def predict(csv_path):
#     model = joblib.load("model/random_forest.pkl")
#     df = load_csv(csv_path)
#     features = create_features(df)
#     X = create_windows(features, WINDOW_SIZE)
#     X = X.reshape(X.shape[0], -1)
#     prediction = model.predict(X)
#     return prediction

# import joblib

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows

# WINDOW_SIZE = 20

# def predict(csv_path):
#     model = joblib.load("model/random_forest.pkl")
#     try:
#         threshold = joblib.load("model/threshold.pkl")
#     except FileNotFoundError:
#         threshold = 0.5

#     df = load_csv(csv_path)
#     features = create_features(df)
#     X = create_windows(features, WINDOW_SIZE)
#     X = X.reshape(X.shape[0], -1)

#     proba = model.predict_proba(X)[:, 1]
#     prediction = (proba >= threshold).astype(int)
#     return prediction

# Règle de persistance
# import numpy as np
# import joblib

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows

# WINDOW_SIZE = 20
# MIN_CONSECUTIVE = 3  # nombre de fenêtres consécutives positives requises pour alerter


# def _smooth(raw_pred, min_consecutive):
#     """N'alerte que si min_consecutive fenêtres consécutives sont positives.
#     Réduit fortement les fausses alertes isolées sans perdre en détection
#     des vrais vols (qui durent toujours plusieurs fenêtres)."""
#     out = np.zeros_like(raw_pred)
#     run = 0
#     for i, v in enumerate(raw_pred):
#         run = run + 1 if v == 1 else 0
#         if run >= min_consecutive:
#             out[i] = 1
#     return out


# def predict(csv_path):
#     model = joblib.load("model/random_forest.pkl")
#     try:
#         threshold = joblib.load("model/threshold.pkl")
#     except FileNotFoundError:
#         threshold = 0.5

#     df = load_csv(csv_path)
#     features = create_features(df)
#     X = create_windows(features, WINDOW_SIZE)
#     X = X.reshape(X.shape[0], -1)

#     proba = model.predict_proba(X)[:, 1]
#     raw_prediction = (proba >= threshold).astype(int)
#     prediction = _smooth(raw_prediction, MIN_CONSECUTIVE)
#     return prediction

# import numpy as np
# import joblib
# import pandas as pd

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows

# WINDOW_SIZE = 20
# MIN_CONSECUTIVE = 3        # persistance exigée pour une alerte issue du modèle ML
# RULE_DROP_THRESHOLD = 0.03  # chute > 3% en un seul relevé, générateur à l'arrêt
# RULE_RECOVERY_WINDOW = 3    # nb de relevés suivants où l'on vérifie un retour au niveau initial
# RULE_RECOVERY_TOL = 0.3     # tolérance de "retour au niveau initial" (30% de l'amplitude de la chute)


# def _smooth(raw_pred, min_consecutive):
#     out = np.zeros_like(raw_pred)
#     run = 0
#     for i, v in enumerate(raw_pred):
#         run = run + 1 if v == 1 else 0
#         if run >= min_consecutive:
#             out[i] = 1
#     return out


# def _rule_based_flags(fuel, status):
#     """
#     Filet de sécurité indépendant du modèle ML : détecte toute chute brutale
#     (> RULE_DROP_THRESHOLD du niveau courant) alors que le générateur est à
#     l'arrêt, ET qui ne revient PAS au niveau initial dans les relevés
#     suivants (ce qui écarterait un simple glitch capteur / faux pic).
#     Retourne un tableau 0/1 par LIGNE (pas par fenêtre).
#     """
#     fuel = fuel.astype(float)
#     delta = np.insert(fuel[1:] - fuel[:-1], 0, 0)
#     rel_delta = np.divide(delta, fuel, out=np.zeros_like(delta, dtype=float), where=fuel != 0)
#     inactive = np.array(["Inactive" in s for s in status])

#     flags = np.zeros(len(fuel), dtype=np.int8)
#     candidates = np.where((rel_delta < -RULE_DROP_THRESHOLD) & inactive)[0]
#     for idx in candidates:
#         if idx == 0:
#             continue
#         pre_drop_level = fuel[idx - 1]
#         drop_amount = abs(fuel[idx - 1] - fuel[idx])
#         end = min(idx + RULE_RECOVERY_WINDOW, len(fuel) - 1)
#         recovered = any(
#             abs(fuel[k] - pre_drop_level) <= RULE_RECOVERY_TOL * drop_amount
#             for k in range(idx, end + 1)
#         )
#         if not recovered:
#             flags[idx] = 1
#     return flags


# def predict(csv_path):
#     model = joblib.load("model/random_forest.pkl")
#     try:
#         threshold = joblib.load("model/threshold.pkl")
#     except FileNotFoundError:
#         threshold = 0.5

#     df = pd.read_csv(csv_path)
#     fuel = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"].to_numpy()
#     status = df["FSA Generator Running [MFSX:01:1:12] (S2)"].to_numpy()

#     # --- prédiction du modèle ML (par fenêtre) ---
#     features = create_features(fuel)
#     X = create_windows(features, WINDOW_SIZE)
#     Xf = X.reshape(X.shape[0], -1)
#     proba = model.predict_proba(Xf)[:, 1]
#     ml_raw = (proba >= threshold).astype(int)
#     ml_pred = _smooth(ml_raw, MIN_CONSECUTIVE)  # par fenêtre

#     # --- règle de sécurité (par ligne) -> on la convertit en alerte "fenêtre" ---
#     rule_flags_by_row = _rule_based_flags(fuel, status)
#     n_windows = len(ml_pred)
#     rule_pred = np.zeros(n_windows, dtype=np.int8)
#     for row_idx in np.where(rule_flags_by_row == 1)[0]:
#         window_start = max(0, row_idx - WINDOW_SIZE + 1)
#         window_end = min(n_windows - 1, row_idx)
#         rule_pred[window_start:window_end + 1] = 1

#     # --- combinaison : alerte si le modèle OU la règle le signale ---
#     final_pred = np.maximum(ml_pred, rule_pred)
#     return final_pred

# Version latest of Claude
# import numpy as np
# import joblib
# import pandas as pd

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows

# WINDOW_SIZE = 20
# MIN_CONSECUTIVE = 3          # persistance exigée pour une alerte issue du modèle ML
# ML_MIN_NET_LOSS_FRAC = 0.03   # une alerte ML n'est retenue que si la fenêtre perd >=3% du niveau

# RULE_DROP_THRESHOLD = 0.03    # chute > 3% en un seul relevé, générateur à l'arrêt
# RULE_RECOVERY_WINDOW = 3
# RULE_RECOVERY_TOL = 0.3


# def _smooth(raw_pred, min_consecutive):
#     out = np.zeros_like(raw_pred)
#     run = 0
#     for i, v in enumerate(raw_pred):
#         run = run + 1 if v == 1 else 0
#         if run >= min_consecutive:
#             out[i] = 1
#     return out


# def _rule_based_flags(fuel, status):
#     fuel = fuel.astype(float)
#     delta = np.insert(fuel[1:] - fuel[:-1], 0, 0)
#     rel_delta = np.divide(delta, fuel, out=np.zeros_like(delta, dtype=float), where=fuel != 0)
#     inactive = np.array(["Inactive" in s for s in status])

#     flags = np.zeros(len(fuel), dtype=np.int8)
#     candidates = np.where((rel_delta < -RULE_DROP_THRESHOLD) & inactive)[0]
#     for idx in candidates:
#         if idx == 0:
#             continue
#         pre_drop_level = fuel[idx - 1]
#         drop_amount = abs(fuel[idx - 1] - fuel[idx])
#         end = min(idx + RULE_RECOVERY_WINDOW, len(fuel) - 1)
#         recovered = any(
#             abs(fuel[k] - pre_drop_level) <= RULE_RECOVERY_TOL * drop_amount
#             for k in range(idx, end + 1)
#         )
#         if not recovered:
#             flags[idx] = 1
#     return flags


# def _magnitude_gate(X):
#     """
#     Ne retient une alerte du modèle ML QUE SI la fenêtre représente une vraie
#     perte nette de carburant (pas un ravitaillement, pas du bruit) :
#       - variation_totale (colonne 1) doit être négative (perte, pas gain)
#       - et représenter au moins ML_MIN_NET_LOSS_FRAC du niveau de départ
#     Filtre à la fois les ravitaillements (variation positive) et le bruit de
#     mesure normal (variation trop faible en proportion).
#     """
#     fuel_debut = X[:, 0]
#     variation_totale = X[:, 1]
#     net_loss_frac = -variation_totale / np.where(fuel_debut != 0, fuel_debut, 1)
#     return (variation_totale < 0) & (net_loss_frac >= ML_MIN_NET_LOSS_FRAC)


# def predict(csv_path):
#     model = joblib.load("model/random_forest.pkl")
#     try:
#         threshold = joblib.load("model/threshold.pkl")
#     except FileNotFoundError:
#         threshold = 0.5

#     df = pd.read_csv(csv_path)
#     fuel = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"].to_numpy()
#     status = df["FSA Generator Running [MFSX:01:1:12] (S2)"].to_numpy()

#     # --- prédiction du modèle ML (par fenêtre) ---
#     features = create_features(fuel)
#     X = create_windows(features, WINDOW_SIZE)
#     Xf = X.reshape(X.shape[0], -1)
#     proba = model.predict_proba(Xf)[:, 1]
#     ml_raw = (proba >= threshold).astype(int)

#     # on ne garde que les alertes ML correspondant à une vraie perte nette significative
#     ml_raw = ml_raw & _magnitude_gate(X)
#     ml_pred = _smooth(ml_raw, MIN_CONSECUTIVE)

#     # --- règle de sécurité (par ligne) -> convertie en alerte "fenêtre" ---
#     rule_flags_by_row = _rule_based_flags(fuel, status)
#     n_windows = len(ml_pred)
#     rule_pred = np.zeros(n_windows, dtype=np.int8)
#     for row_idx in np.where(rule_flags_by_row == 1)[0]:
#         window_start = max(0, row_idx - WINDOW_SIZE + 1)
#         window_end = min(n_windows - 1, row_idx)
#         rule_pred[window_start:window_end + 1] = 1

#     final_pred = np.maximum(ml_pred, rule_pred)
#     return final_pred

# Version qui utilise intelligement l'état du générateur
import numpy as np
import joblib
import pandas as pd

from src.preprocess import load_csv
from src.features import create_features
from src.windows import create_windows

WINDOW_SIZE = 20
MIN_CONSECUTIVE = 3

RULE_DROP_MULTIPLIER = 5
GATE_LOSS_MULTIPLIER = 2.5
RECOVERY_WINDOW = 3
RECOVERY_TOL = 0.3
MIN_SCALE_FLOOR = 1.0
MIN_STATE_ROWS = 10   # nombre minimal de lignes dans CHAQUE état pour juger le statut exploitable
SCALE_PERCENTILE = 90  # percentile robuste (moins sensible qu'un 99e a une contamination par l'anomalie elle-meme, surtout sur peu d'echantillons)


def _smooth(raw_pred, min_consecutive):
    out = np.zeros_like(raw_pred)
    run = 0
    for i, v in enumerate(raw_pred):
        run = run + 1 if v == 1 else 0
        if run >= min_consecutive:
            out[i] = 1
    return out


def _status_is_reliable(active):
    """
    Le statut Actif/Inactif n'est exploité que si les DEUX états ont été
    observés un nombre suffisant de fois (en nombre absolu de lignes, pas en
    pourcentage : un groupe de secours peut légitimement n'être actif que
    2-3% du temps sans que son statut soit pour autant douteux).
    """
    n_active = int(active.sum())
    n_inactive = int((~active).sum())
    return n_active >= MIN_STATE_ROWS and n_inactive >= MIN_STATE_ROWS


def _site_scales(fuel, active, status_reliable):
    delta = np.insert(fuel[1:] - fuel[:-1], 0, 0)

    if status_reliable:
        inactive = ~active
        noise_vals = np.abs(delta[inactive])
        noise_scale = max(float(np.percentile(noise_vals, SCALE_PERCENTILE)), MIN_SCALE_FLOOR) if len(noise_vals) else MIN_SCALE_FLOOR

        consumption_vals = -delta[active]
        consumption_vals = consumption_vals[consumption_vals > 0]
        active_scale = max(float(np.percentile(consumption_vals, SCALE_PERCENTILE)), MIN_SCALE_FLOOR) if len(consumption_vals) else MIN_SCALE_FLOOR
    else:
        # Mode dégradé : le statut n'est pas informatif sur ce fichier.
        # On calibre une échelle UNIQUE à partir de toutes les baisses de
        # niveau observées (quel que soit le statut rapporté), et on
        # l'applique de façon identique partout. Moins précis qu'un vrai
        # statut fiable, mais évite de dépendre d'un signal cassé.
        consumption_vals = -delta
        consumption_vals = consumption_vals[consumption_vals > 0]
        scale = max(float(np.percentile(consumption_vals, SCALE_PERCENTILE)), MIN_SCALE_FLOOR) if len(consumption_vals) else MIN_SCALE_FLOOR
        noise_scale = active_scale = scale

    return noise_scale, active_scale


def _rule_based_flags(fuel, active, noise_scale, status_reliable):
    delta = np.insert(fuel[1:] - fuel[:-1], 0, 0)
    drop_threshold = RULE_DROP_MULTIPLIER * noise_scale

    # Si le statut n'est pas fiable, on ne peut plus se limiter aux périodes
    # "à l'arrêt" -> on applique la règle sur TOUT le fichier (le seuil de
    # dérive vient du mode dégradé, plus conservateur).
    eligible = np.ones(len(fuel), dtype=bool) if not status_reliable else ~active

    flags = np.zeros(len(fuel), dtype=np.int8)
    candidates = np.where((delta < -drop_threshold) & eligible)[0]
    for idx in candidates:
        if idx == 0:
            continue
        pre_drop_level = fuel[idx - 1]
        drop_amount = abs(fuel[idx - 1] - fuel[idx])
        end = min(idx + RECOVERY_WINDOW, len(fuel) - 1)
        recovered = any(
            abs(fuel[k] - pre_drop_level) <= RECOVERY_TOL * drop_amount
            for k in range(idx, end + 1)
        )
        if not recovered:
            flags[idx] = 1
    return flags


def _magnitude_gate(X, active, noise_scale, active_scale, status_reliable):
    n = X.shape[0]
    if status_reliable:
        cum_active = np.concatenate(([0], np.cumsum(active.astype(int))))
        n_active_in_window = cum_active[WINDOW_SIZE:WINDOW_SIZE + n] - cum_active[0:n]
        n_inactive_in_window = WINDOW_SIZE - n_active_in_window
        expected_ceiling = n_active_in_window * active_scale + n_inactive_in_window * noise_scale
    else:
        # mode dégradé : une échelle unique appliquée à toute la fenêtre
        expected_ceiling = np.full(n, WINDOW_SIZE * noise_scale)

    variation_totale = X[:, 1]
    return variation_totale < -(GATE_LOSS_MULTIPLIER * expected_ceiling)


def predict(csv_path):
    model = joblib.load("model/random_forest.pkl")
    try:
        threshold = joblib.load("model/threshold.pkl")
    except FileNotFoundError:
        threshold = 0.5

    df = pd.read_csv(csv_path)
    fuel = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"].to_numpy().astype(float)
    status = df["FSA Generator Running [MFSX:01:1:12] (S2)"].to_numpy()
    active = np.array(["Active" in s for s in status])

    status_reliable = _status_is_reliable(active)
    noise_scale, active_scale = _site_scales(fuel, active, status_reliable)

    features = create_features(fuel)
    X = create_windows(features, WINDOW_SIZE)
    Xf = X.reshape(X.shape[0], -1)
    proba = model.predict_proba(Xf)[:, 1]
    ml_raw = (proba >= threshold).astype(int)
    ml_raw = ml_raw & _magnitude_gate(X, active, noise_scale, active_scale, status_reliable)
    ml_pred = _smooth(ml_raw, MIN_CONSECUTIVE)

    rule_flags_by_row = _rule_based_flags(fuel, active, noise_scale, status_reliable)
    n_windows = len(ml_pred)
    rule_pred = np.zeros(n_windows, dtype=np.int8)
    for row_idx in np.where(rule_flags_by_row == 1)[0]:
        window_start = max(0, row_idx - WINDOW_SIZE + 1)
        window_end = min(n_windows - 1, row_idx)
        rule_pred[window_start:window_end + 1] = 1

    final_pred = np.maximum(ml_pred, rule_pred)
    return final_pred