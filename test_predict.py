"""
Teste le modèle entraîné sur un seul fichier CSV.

Usage :
    python test_predict.py chemin/vers/fichier.csv

Prérequis : model/random_forest.pkl (et model/threshold.pkl) doivent exister.
"""

import sys

import numpy as np

from src.config import TIME_COL
from src.predict import predict, WINDOW_SIZE
from src.preprocess import load_site


def group_consecutive(indices):
    """Regroupe des indices triés en intervalles consécutifs [(début, fin), ...]."""
    indices = np.asarray(indices)
    if len(indices) == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) != 1)
    starts = np.concatenate(([indices[0]], indices[breaks + 1]))
    ends = np.concatenate((indices[breaks], [indices[-1]]))
    return list(zip(starts.tolist(), ends.tolist()))


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_predict.py chemin/vers/fichier.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    prediction = predict(csv_path)  # 0/1 par fenêtre, après les règles

    print(f"Fichier : {csv_path}")
    print(f"Fenêtres totales analysées : {len(prediction)}")
    print(f"Fenêtres en alerte : {int(prediction.sum())}")

    events = group_consecutive(np.flatnonzero(prediction == 1))
    if not events:
        print("\n✅ Aucun vol détecté sur ce fichier.")
        return

    fuel, _, timestamps = load_site(csv_path)
    last_row = len(fuel) - 1
    if timestamps is None:
        print(f"(colonne {TIME_COL!r} absente : seuls les numéros de ligne sont affichés)")

    print(f"\n⚠️  {len(events)} période(s) suspecte(s) détectée(s) :\n")
    for window_start, window_end in events:
        row_start = window_start
        row_end = min(window_end + WINDOW_SIZE - 1, last_row)
        when = f"  |  {timestamps[row_start]}  ->  {timestamps[row_end]}" if timestamps is not None else ""
        print(f"  Lignes {row_start}-{row_end}{when}")


if __name__ == "__main__":
    main()
