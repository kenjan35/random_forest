"""
Teste le modèle entraîné sur un seul fichier CSV.

Usage :
    python test_predict.py chemin/vers/fichier.csv

Prérequis : avoir déjà lancé `python main.py` au moins une fois
(model/random_forest.pkl et model/threshold.pkl doivent exister).
"""

import sys
import pandas as pd

from src.predict import predict, WINDOW_SIZE


def group_consecutive(indices):
    """Regroupe une liste d'indices triés en intervalles consécutifs."""
    if len(indices) == 0:
        return []
    groups = []
    start = prev = indices[0]
    for idx in indices[1:]:
        if idx == prev + 1:
            prev = idx
        else:
            groups.append((start, prev))
            start = prev = idx
    groups.append((start, prev))
    return groups


def main():
    if len(sys.argv) != 2:
        print("Usage: python test_predict.py chemin/vers/fichier.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    prediction = predict(csv_path)  # 0/1 par fenêtre, après la règle de persistance

    n_alert_windows = int(prediction.sum())
    print(f"Fichier : {csv_path}")
    print(f"Fenêtres totales analysées : {len(prediction)}")
    print(f"Fenêtres en alerte : {n_alert_windows}")

    alert_indices = [i for i, v in enumerate(prediction) if v == 1]
    events = group_consecutive(alert_indices)

    if not events:
        print("\n✅ Aucun vol détecté sur ce fichier.")
        return

    # on relit les timestamps pour donner un horodatage lisible aux alertes
    df = pd.read_csv(csv_path)
    timestamps = df["Time stamp"].to_numpy()

    print(f"\n⚠️  {len(events)} période(s) suspecte(s) détectée(s) :\n")
    for (window_start, window_end) in events:
        row_start = window_start
        row_end = window_end + WINDOW_SIZE - 1
        row_end = min(row_end, len(timestamps) - 1)
        print(f"  Lignes {row_start}-{row_end}  |  {timestamps[row_start]}  ->  {timestamps[row_end]}")


if __name__ == "__main__":
    main()