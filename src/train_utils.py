import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, precision_recall_curve
from src.config import MODEL_DIR, MODEL_PATH, THRESHOLD_PATH

def _print_distribution(y):
    vals, counts = np.unique(y, return_counts=True)
    print("Distribution y:", dict(zip(vals.tolist(), counts.tolist())))


def _split_by_group(X, y, groups):
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    return X[train_idx], X[test_idx], y[train_idx], y[test_idx]


def _create_model():
    return RandomForestClassifier(
        n_estimators=300, random_state=42, class_weight="balanced_subsample",
        n_jobs=-1, min_samples_leaf=2,
    )


def _select_threshold(y_test, proba):
    print("=== Seuil 0.5 (défaut) — fichiers jamais vus ===")
    print(classification_report(y_test, (proba >= 0.5).astype(int), zero_division=0))
    precisions, recalls, thresholds = precision_recall_curve(y_test, proba)
    f1s = 2 * precisions * recalls / (precisions + recalls + 1e-12)
    best_threshold = float(thresholds[np.argmax(f1s[:-1])])
    print(f"=== Seuil optimisé ({best_threshold:.3f}) — fichiers jamais vus ===")
    print(classification_report(y_test, (proba >= best_threshold).astype(int), zero_division=0))
    return best_threshold


def _save_artifacts(model, threshold):
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(threshold, THRESHOLD_PATH)


