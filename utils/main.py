"""
Entraîne le modèle sur data/ + annotations.csv et sauvegarde
model/random_forest.pkl et model/threshold.pkl.
"""

import os
import sys

# Permet de lancer ce script depuis utils/ (ou n'importe quel dossier) :
# la racine du projet (qui contient src/) est ajoutée au chemin d'import.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.dataset import build_dataset
from src.train import train

DATA_FOLDER = os.path.join(ROOT, "data")
ANNOTATIONS = os.path.join(ROOT, "annotations.csv")


def main():
    X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)
    print(X.shape, y.shape)
    train(X, y, groups)


if __name__ == "__main__":
    main()
