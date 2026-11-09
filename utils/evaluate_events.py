"""
Évaluation "métier" du modèle : métriques par évènement et fausses alertes.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from sklearn.metrics import classification_report
from sklearn.model_selection import GroupShuffleSplit
from src.dataset import (
    build_dataset, list_csv_files, load_annotations, WINDOW_SIZE,
)
from src.predict import _smooth, load_model

DATA_FOLDER = os.path.join(ROOT, "data")
ANNOTATIONS = os.path.join(ROOT, "annotations.csv")
PERSISTENCE_VALUES = [1, 2, 3, 5, 8]

def main():
    X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)
    test_idx = _test_indices(X, y, groups)
    model, threshold = load_model()
    print(f"Seuil utilisé : {threshold}")
    raw_pred = (model.predict_proba(X[test_idx])[:, 1] >= threshold).astype(int)
    _print_evaluation(y[test_idx], raw_pred, groups[test_idx])
    missed = _compare_persistence(raw_pred, groups[test_idx])
    print(f"\nVols manqués avec la dernière règle testée (MIN_CONSECUTIVE={PERSISTENCE_VALUES[-1]}) :")
    for fname, s, e in missed:
        print(f"  {fname}  lignes {s}-{e}")


from utils.evaluate_events_utils import evaluate, _evaluate_intervals, _test_indices, _print_evaluation, _compare_persistence

if __name__ == "__main__":
    main()
