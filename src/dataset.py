import os
import glob

import numpy as np
import pandas as pd

from src.config import WINDOW_SIZE  # ré-exporté pour evaluate_events.py
from src.preprocess import load_csv
from src.features import create_features
from src.windows import create_windows
from src.labels import create_labels


def load_annotations(path):
    """{nom_de_fichier: [(start, end), ...]} avec des indices entiers."""
    df = pd.read_csv(path, usecols=["filename", "start", "end"])
    df["filename"] = df["filename"].astype(str).str.strip()
    df[["start", "end"]] = df[["start", "end"]].astype(int)
    return {
        name: list(zip(group["start"].tolist(), group["end"].tolist()))
        for name, group in df.groupby("filename", sort=False)
    }


def list_csv_files(data_folder):
    """Liste triée des CSV (l'ordre définit l'index de groupe de chaque fichier)."""
    return sorted(glob.glob(os.path.join(data_folder, "**", "*.csv"), recursive=True))


def build_dataset(data_folder, annotations_file):
    """
    Retourne X, y, groups.
    `groups` associe chaque fenêtre à l'index de son fichier source, pour
    permettre un split train/test PAR FICHIER (voir train.py) et éviter
    toute fuite de données entre fenêtres qui se chevauchent.
    """
    annotations = load_annotations(annotations_file)
    csv_files = list_csv_files(data_folder)
    if not csv_files:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans {data_folder!r}")

    names = [os.path.basename(f) for f in csv_files]
    duplicates = sorted({n for n in names if names.count(n) > 1})
    if duplicates:
        print(f"ATTENTION : noms de fichiers en double, annotations partagées : {duplicates}")

    all_X, all_y, all_groups = [], [], []
    for file_idx, (csv_file, filename) in enumerate(zip(csv_files, names)):
        X = create_windows(create_features(load_csv(csv_file)), WINDOW_SIZE)
        y = create_labels(len(X), WINDOW_SIZE, annotations.get(filename, []))
        all_X.append(X)
        all_y.append(y)
        all_groups.append(np.full(len(X), file_idx))

    return np.concatenate(all_X), np.concatenate(all_y), np.concatenate(all_groups)
