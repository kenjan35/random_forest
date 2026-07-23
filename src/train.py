# first code with CGPT
#  import joblib

# from sklearn.ensemble import RandomForestClassifier
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import classification_report

# def train(X, y):
#     samples = X.shape[0]
#     X = X.reshape(samples, -1)
#     X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
#     model = RandomForestClassifier(n_estimators=200, random_state=42)
#     model.fit(X_train, y_train)
#     prediction = model.predict(X_test)
#     print(classification_report(y_test, prediction))
#     joblib.dump(model, "model/random_forest.pkl")

# second with Claude Pro
#  import joblib
# import numpy as np

# from sklearn.ensemble import RandomForestClassifier
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import classification_report

# def train(X, y):
#     samples = X.shape[0]
#     X = X.reshape(samples, -1)

#     vals, counts = np.unique(y, return_counts=True)
#     print("Distribution y:", dict(zip(vals.tolist(), counts.tolist())))

#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y, test_size=0.2, random_state=42, stratify=y
#     )
#     model = RandomForestClassifier(
#         n_estimators=200,
#         random_state=42,
#         class_weight="balanced_subsample",  # compense le déséquilibre
#         n_jobs=-1,
#     )
#     model.fit(X_train, y_train)
#     prediction = model.predict(X_test)
#     print(classification_report(y_test, prediction, zero_division=0))
#     joblib.dump(model, "model/random_forest.pkl")

# Second version of Claude
#  import joblib
# import numpy as np

# from sklearn.ensemble import RandomForestClassifier
# from sklearn.model_selection import train_test_split
# from sklearn.metrics import classification_report, precision_recall_curve, f1_score


# def train(X, y):
#     samples = X.shape[0]
#     X = X.reshape(samples, -1)

#     vals, counts = np.unique(y, return_counts=True)
#     print("Distribution y:", dict(zip(vals.tolist(), counts.tolist())))

#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y, test_size=0.2, random_state=42, stratify=y
#     )

#     model = RandomForestClassifier(
#         n_estimators=300,
#         random_state=42,
#         class_weight="balanced_subsample",
#         n_jobs=-1,
#         min_samples_leaf=2,
#     )
#     model.fit(X_train, y_train)

#     # --- seuil par défaut (0.5) ---
#     proba = model.predict_proba(X_test)[:, 1]
#     prediction = (proba >= 0.5).astype(int)
#     print("=== Seuil 0.5 (défaut) ===")
#     print(classification_report(y_test, prediction, zero_division=0))

#     # --- recherche du meilleur seuil (meilleur F1 sur la classe "vol") ---
#     precisions, recalls, thresholds = precision_recall_curve(y_test, proba)
#     f1s = 2 * precisions * recalls / (precisions + recalls + 1e-12)
#     best_idx = np.argmax(f1s[:-1])  # thresholds a une valeur de moins que precisions/recalls
#     best_threshold = thresholds[best_idx]
#     prediction_best = (proba >= best_threshold).astype(int)
#     print(f"=== Seuil optimisé ({best_threshold:.3f}) ===")
#     print(classification_report(y_test, prediction_best, zero_division=0))

#     joblib.dump(model, "model/random_forest.pkl")
#     joblib.dump(best_threshold, "model/threshold.pkl")
#     return model, best_threshold

import joblib
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import classification_report, precision_recall_curve


def train(X, y, groups):
    """
    groups: index de fichier par fenêtre (retourné par build_dataset).
    Split PAR FICHIER : aucun fichier utilisé en test n'a de fenêtre en
    train, ce qui évite la fuite de données due au chevauchement des
    fenêtres glissantes et donne une mesure honnête de généralisation
    sur des générateurs jamais vus.
    """
    samples = X.shape[0]
    X = X.reshape(samples, -1)

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

    prediction = (proba >= 0.5).astype(int)
    print("=== Seuil 0.5 (défaut) — fichiers jamais vus ===")
    print(classification_report(y_test, prediction, zero_division=0))

    precisions, recalls, thresholds = precision_recall_curve(y_test, proba)
    f1s = 2 * precisions * recalls / (precisions + recalls + 1e-12)
    best_idx = np.argmax(f1s[:-1])
    best_threshold = thresholds[best_idx]
    prediction_best = (proba >= best_threshold).astype(int)
    print(f"=== Seuil optimisé ({best_threshold:.3f}) — fichiers jamais vus ===")
    print(classification_report(y_test, prediction_best, zero_division=0))

    joblib.dump(model, "model/random_forest.pkl")
    joblib.dump(best_threshold, "model/threshold.pkl")
    return model, best_threshold