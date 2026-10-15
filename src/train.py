import os

import joblib
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, precision_recall_curve

from src.config import MODEL_DIR, MODEL_PATH, THRESHOLD_PATH


def train(X, y, groups):
    """
    groups: index de fichier par fenêtre (retourné par build_dataset).
    Split PAR FICHIER : aucun fichier utilisé en test n'a de fenêtre en
    train, ce qui évite la fuite de données due au chevauchement des
    fenêtres glissantes.
    """
    X = X.reshape(X.shape[0], -1)

    vals, counts = np.unique(y, return_counts=True)
    print("Distribution y:", dict(zip(vals.tolist(), counts.tolist())))

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    model = RandomForestClassifier(
        n_estimators=300,
        random_state=42,
        class_weight="balanced_subsample",
        n_jobs=-1,
        min_samples_leaf=2,
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]

    print("=== Seuil 0.5 (défaut) — fichiers jamais vus ===")
    print(classification_report(y_test, (proba >= 0.5).astype(int), zero_division=0))

    precisions, recalls, thresholds = precision_recall_curve(y_test, proba)
    f1s = 2 * precisions * recalls / (precisions + recalls + 1e-12)
    best_threshold = float(thresholds[np.argmax(f1s[:-1])])
    print(f"=== Seuil optimisé ({best_threshold:.3f}) — fichiers jamais vus ===")
    print(classification_report(y_test, (proba >= best_threshold).astype(int), zero_division=0))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(best_threshold, THRESHOLD_PATH)
    return model, best_threshold
