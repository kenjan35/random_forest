# """
# Évaluation "métier" du modèle : au-delà du recall par fenêtre, on regarde
# si CHAQUE VOL RÉEL a déclenché au moins une alerte (recall par évènement),
# et si les fichiers normaux (sans vol) génèrent des fausses alertes.

# À lancer après main.py (qui doit avoir produit model/random_forest.pkl
# et model/threshold.pkl).
# """

# import os
# import glob
# import numpy as np
# import joblib

# from src.dataset import build_dataset, load_annotations, WINDOW_SIZE
# from sklearn.model_selection import GroupShuffleSplit
# from sklearn.metrics import classification_report

# DATA_FOLDER = "data"
# ANNOTATIONS = "annotations.csv"


# def main():
#     X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)
#     X_flat = X.reshape(X.shape[0], -1)

#     # Reproduit exactement le split utilisé dans train.py (mêmes paramètres)
#     splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
#     train_idx, test_idx = next(splitter.split(X_flat, y, groups))

#     model = joblib.load("model/random_forest.pkl")
#     try:
#         threshold = joblib.load("model/threshold.pkl")
#     except FileNotFoundError:
#         threshold = 0.5
#     print(f"Seuil utilisé : {threshold}")

#     proba = model.predict_proba(X_flat[test_idx])[:, 1]
#     pred = (proba >= threshold).astype(int)
#     y_test = y[test_idx]

#     print("\n=== Niveau fenêtre ===")
#     print(classification_report(y_test, pred, zero_division=0))

#     annotations = load_annotations(ANNOTATIONS)
#     csv_files = sorted(glob.glob(os.path.join(DATA_FOLDER, "**", "*.csv"), recursive=True))
#     groups_test = groups[test_idx]
#     test_file_indices = sorted(set(groups_test.tolist()))

#     detected, missed = [], []
#     clean_files_total, clean_files_with_false_alarm = 0, 0

#     for gi in test_file_indices:
#         fname = os.path.basename(csv_files[gi])
#         mask = (groups_test == gi)
#         pred_file = pred[mask]  # ordre préservé : fenêtres du fichier, dans l'ordre

#         intervals = annotations.get(fname, [])
#         if intervals:
#             for (s, e) in intervals:
#                 window_start = max(0, s - (WINDOW_SIZE - 1))
#                 window_end = e
#                 hit = any(
#                     0 <= wi < len(pred_file) and pred_file[wi] == 1
#                     for wi in range(window_start, window_end + 1)
#                 )
#                 (detected if hit else missed).append((fname, s, e))
#         else:
#             clean_files_total += 1
#             if pred_file.sum() > 0:
#                 clean_files_with_false_alarm += 1

#     total_events = len(detected) + len(missed)
#     print("\n=== Niveau évènement (au moins 1 fenêtre correcte = vol détecté) ===")
#     if total_events:
#         print(f"Détectés : {len(detected)}/{total_events}  (taux = {len(detected)/total_events:.3f})")
#     else:
#         print("Aucun évènement de vol dans le jeu de test.")

#     if missed:
#         print("\nVols manqués (à investiguer) :")
#         for fname, s, e in missed:
#             print(f"  {fname}  lignes {s}-{e}")

#     print("\n=== Fausses alertes sur fichiers normaux (jamais annotés) ===")
#     if clean_files_total:
#         rate = clean_files_with_false_alarm / clean_files_total
#         print(f"Fichiers propres avec >=1 fausse alerte : {clean_files_with_false_alarm}/{clean_files_total}  (taux = {rate:.3f})")
#     else:
#         print("Aucun fichier normal dans le jeu de test.")


# if __name__ == "__main__":
#     main()

"""
Évaluation "métier" du modèle : au-delà du recall par fenêtre, on regarde
si CHAQUE VOL RÉEL a déclenché au moins une alerte (recall par évènement),
et si les fichiers normaux (sans vol) génèrent des fausses alertes.

Teste plusieurs règles de persistance (MIN_CONSECUTIVE) pour trouver le
meilleur compromis détection / fausses alertes.

À lancer après main.py (qui doit avoir produit model/random_forest.pkl
et model/threshold.pkl).
"""

import os
import glob
import numpy as np
import joblib

from src.dataset import build_dataset, load_annotations, WINDOW_SIZE
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report

DATA_FOLDER = "data"
ANNOTATIONS = "annotations.csv"


def smooth(raw_pred, min_consecutive):
    """N'alerte que si `min_consecutive` fenêtres consécutives sont positives."""
    out = np.zeros_like(raw_pred)
    run = 0
    for i, v in enumerate(raw_pred):
        run = run + 1 if v == 1 else 0
        if run >= min_consecutive:
            out[i] = 1
    return out


def evaluate(raw_pred, groups_test, annotations, csv_files, test_file_indices, min_consecutive):
    detected, missed, missed_list = 0, 0, []
    clean_total, clean_false = 0, 0

    for gi in test_file_indices:
        fname = os.path.basename(csv_files[gi])
        mask = (groups_test == gi)
        pred_file = smooth(raw_pred[mask], min_consecutive)

        intervals = annotations.get(fname, [])
        if intervals:
            for (s, e) in intervals:
                window_start = max(0, s - (WINDOW_SIZE - 1))
                window_end = e
                hit = any(
                    0 <= wi < len(pred_file) and pred_file[wi] == 1
                    for wi in range(window_start, window_end + 1)
                )
                if hit:
                    detected += 1
                else:
                    missed += 1
                    missed_list.append((fname, s, e))
        else:
            clean_total += 1
            if pred_file.sum() > 0:
                clean_false += 1

    return detected, missed, missed_list, clean_total, clean_false


def main():
    X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)
    X_flat = X.reshape(X.shape[0], -1)

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X_flat, y, groups))

    model = joblib.load("model/random_forest.pkl")
    try:
        threshold = joblib.load("model/threshold.pkl")
    except FileNotFoundError:
        threshold = 0.5
    print(f"Seuil utilisé : {threshold}")

    proba = model.predict_proba(X_flat[test_idx])[:, 1]
    raw_pred = (proba >= threshold).astype(int)
    y_test = y[test_idx]

    print("\n=== Niveau fenêtre (sans persistance) ===")
    print(classification_report(y_test, raw_pred, zero_division=0))

    annotations = load_annotations(ANNOTATIONS)
    csv_files = sorted(glob.glob(os.path.join(DATA_FOLDER, "**", "*.csv"), recursive=True))
    groups_test = groups[test_idx]
    test_file_indices = sorted(set(groups_test.tolist()))

    print("\n=== Comparatif des règles de persistance ===")
    print(f"{'MIN_CONSECUTIVE':>16} | {'evenements detectes':>20} | {'fichiers propres avec fausse alerte':>36}")
    last_missed = None
    for mc in [1, 2, 3, 5, 8]:
        detected, missed, missed_list, clean_total, clean_false = evaluate(
            raw_pred, groups_test, annotations, csv_files, test_file_indices, mc
        )
        total = detected + missed
        det_rate = detected / total if total else 0
        false_rate = clean_false / clean_total if clean_total else 0
        print(f"{mc:>16} | {detected}/{total} ({det_rate:.3f}){'':>4} | {clean_false}/{clean_total} ({false_rate:.3f})")
        last_missed = missed_list

    print("\nVols manqués avec la dernière règle testée (MIN_CONSECUTIVE=8) :")
    for fname, s, e in last_missed:
        print(f"  {fname}  lignes {s}-{e}")


if __name__ == "__main__":
    main()