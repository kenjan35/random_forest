"""
Entraîne le modèle sur data/ + annotations.csv et sauvegarde
model/random_forest.pkl et model/threshold.pkl.
"""

from src.dataset import build_dataset
from src.train import train

DATA_FOLDER = "data"
ANNOTATIONS = "annotations.csv"


def main():
    X, y, groups = build_dataset(DATA_FOLDER, ANNOTATIONS)
    print(X.shape, y.shape)
    train(X, y, groups)


if __name__ == "__main__":
    main()
