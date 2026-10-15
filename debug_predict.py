"""
Affiche, fenêtre par fenêtre, la probabilité de vol calculée par le modèle
entraîné (model/random_forest.pkl), sans règles ni persistance — pour voir
exactement ce que le modèle "pense" de chaque fenêtre.

Usage :
    python debug_predict.py data/test/TATS086.csv
"""

import sys

import numpy as np

from src.config import WINDOW_SIZE
from src.features import create_features
from src.predict import load_model
from src.preprocess import load_csv
from src.windows import create_windows


def main():
    if len(sys.argv) != 2:
        print("Usage: python debug_predict.py chemin/vers/fichier.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    model, threshold = load_model()

    X = create_windows(create_features(load_csv(csv_path)), WINDOW_SIZE)
    if len(X) == 0:
        print(f"Fichier trop court (moins de {WINDOW_SIZE} relevés).")
        return

    proba = model.predict_proba(X)[:, 1]

    print(f"Fichier : {csv_path}")
    print(f"n_features_in_ du modèle : {model.n_features_in_}  |  features fournies : {X.shape[1]}")
    print(f"Seuil : {threshold}")
    print(f"Proba max sur tout le fichier : {proba.max():.4f}  (fenêtre {proba.argmax()})")
    print(f"Proba moyenne : {proba.mean():.4f}")
    print(f"Nombre de fenêtres avec proba > 0.1 : {(proba > 0.1).sum()}")
    print(f"Nombre de fenêtres avec proba >= seuil ({threshold:.3f}) : {(proba >= threshold).sum()}")

    top20 = np.sort(np.argsort(proba)[::-1][:20])
    print("\nTop 20 fenêtres les plus suspectes selon le modèle :")
    for idx in top20:
        print(f"  fenêtre {idx:5d} (lignes {idx}-{idx + WINDOW_SIZE - 1})  proba={proba[idx]:.4f}  "
              f"fuel_debut={X[idx, 0]:.1f}  variation_totale={X[idx, 1]:.1f}  min_delta={X[idx, 4]:.1f}")


if __name__ == "__main__":
    main()
