"""
Évaluation "métier" du modèle : au-delà du recall par fenêtre, on regarde
si CHAQUE VOL RÉEL a déclenché au moins une alerte (recall par évènement),
et si les fichiers normaux (sans vol) génèrent des fausses alertes.

Teste plusieurs règles de persistance (MIN_CONSECUTIVE) pour trouver le
meilleur compromis détection / fausses alertes.

Attention : n'évalue que la partie ML (seuil + persistance), pas les règles
de src/predict.py.
"""

import os

from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit

from src.dataset import build_dataset, list_csv_files, load_annotations, WINDOW_SIZE
from src.predict import _smooth, load_model

DATA_FOLDER = "data"
ANNOTATIONS = "annotations.csv"
PERSISTENCE_VALUES = [1, 2, 3, 5, 8]


def evaluate(raw_pred, groups_test, annotations, csv_files, min_consecutive):
    detected, missed_list = 0, []
    clean_total, clean_false = 0, 0

    for gi in sorted(set(groups_test.tolist())):
        fname = os.path.basename(csv_files[gi])
        pred_file = _smooth(raw_pred[groups_test == gi], min_consecutive)

        intervals = annotations.get(fname, [])
        if not intervals:
            clean_total += 1
            clean_false += int(pred_file.any())
            continue

        for s, e in intervals:
            # fenêtres qui chevauchent les lignes s..e
            if pred_file[max(0, s - (WINDOW_SIZE - 1)):e + 1].any():
                detected += 1
            else:
                missed_list.append((fname, s, e))

    return detected, missed_list, clean_total, clean_false


def main():
    X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)

    # même split que train.py
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    _, test_idx = next(splitter.split(X, y, groups))

    model, threshold = load_model()
    print(f"Seuil utilisé : {threshold}")

    raw_pred = (model.predict_proba(X[test_idx])[:, 1] >= threshold).astype(int)

    print("\n=== Niveau fenêtre (sans persistance) ===")
    print(classification_report(y[test_idx], raw_pred, zero_division=0))

    annotations = load_annotations(ANNOTATIONS)
    csv_files = list_csv_files(DATA_FOLDER)
    groups_test = groups[test_idx]

    print("\n=== Comparatif des règles de persistance ===")
    print(f"{'MIN_CONSECUTIVE':>16} | {'evenements detectes':>20} | {'fichiers propres avec fausse alerte':>36}")
    missed_list = []
    for mc in PERSISTENCE_VALUES:
        detected, missed_list, clean_total, clean_false = evaluate(
            raw_pred, groups_test, annotations, csv_files, mc
        )
        total = detected + len(missed_list)
        det_rate = detected / total if total else 0
        false_rate = clean_false / clean_total if clean_total else 0
        print(f"{mc:>16} | {detected}/{total} ({det_rate:.3f}){'':>4} | {clean_false}/{clean_total} ({false_rate:.3f})")

    print(f"\nVols manqués avec la dernière règle testée (MIN_CONSECUTIVE={PERSISTENCE_VALUES[-1]}) :")
    for fname, s, e in missed_list:
        print(f"  {fname}  lignes {s}-{e}")


if __name__ == "__main__":
    main()
