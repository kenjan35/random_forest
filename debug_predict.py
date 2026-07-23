"""
Affiche, fenêtre par fenêtre, la probabilité de vol calculée par VOTRE modèle
entraîné (model/random_forest.pkl), sans la règle de persistance ni le
seuillage — pour voir exactement ce que le modèle "pense" de chaque fenêtre.

Usage :
    python debug_predict.py data/test/TATS086.csv
"""

import sys
import numpy as np
import joblib

from src.preprocess import load_csv
from src.features import create_features
from src.windows import create_windows

WINDOW_SIZE = 20


def main():
    csv_path = sys.argv[1]
    model = joblib.load("model/random_forest.pkl")
    try:
        threshold = joblib.load("model/threshold.pkl")
    except FileNotFoundError:
        threshold = 0.5

    fuel = load_csv(csv_path)
    features = create_features(fuel)
    X = create_windows(features, WINDOW_SIZE)
    Xf = X.reshape(X.shape[0], -1)

    proba = model.predict_proba(Xf)[:, 1]

    print(f"Fichier : {csv_path}")
    print(f"n_features_in_ du modèle : {model.n_features_in_}  |  features fournies : {Xf.shape[1]}")
    print(f"Seuil : {threshold}")
    print(f"Proba max sur tout le fichier : {proba.max():.4f}  (fenêtre {proba.argmax()})")
    print(f"Proba moyenne : {proba.mean():.4f}")
    print(f"Nombre de fenêtres avec proba > 0.1 : {(proba > 0.1).sum()}")
    print(f"Nombre de fenêtres avec proba > seuil ({threshold:.3f}) : {(proba > threshold).sum()}")

    top20 = np.argsort(proba)[::-1][:20]
    print("\nTop 20 fenêtres les plus suspectes selon le modèle :")
    for idx in sorted(top20):
        print(f"  fenêtre {idx:5d} (lignes {idx}-{idx+WINDOW_SIZE-1})  proba={proba[idx]:.4f}  "
              f"fuel_debut={X[idx][0]:.1f}  variation_totale={X[idx][1]:.1f}  min_delta={X[idx][4]:.1f}")


if __name__ == "__main__":
    main()