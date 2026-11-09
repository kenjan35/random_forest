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
    _print_distribution(y)
    X_train, X_test, y_train, y_test = _split_by_group(X, y, groups)
    model = _create_model()
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    best_threshold = _select_threshold(y_test, proba)
    _save_artifacts(model, best_threshold)
    return model, best_threshold


from src.train_utils import _print_distribution, _split_by_group, _create_model, _select_threshold, _save_artifacts
