# import os
# import glob

# import numpy as np
# import pandas as pd

# from src.preprocess import load_csv
# from src.features import create_features
# from src.windows import create_windows
# from src.labels import create_labels

# WINDOW_SIZE = 20

# def load_annotations(path):
#     annotations = {}
#     df = pd.read_csv(path)
#     for _, row in df.iterrows():
#         filename = row["filename"]
#         start = row["start"]
#         end = row["end"]
#         annotations.setdefault(filename, []).append((start, end))
#     return annotations


# def build_dataset(data_folder, annotations_file):
#     annotations = load_annotations(annotations_file)
#     all_X = []
#     all_y = []
#     csv_files = glob.glob(os.path.join(data_folder, "**", "*.csv"), recursive=True)
#     for csv_file in csv_files:
#         df = load_csv(csv_file)
#         features = create_features(df)
#         X = create_windows(features, WINDOW_SIZE)
#         filename = os.path.basename(csv_file)
#         theft_intervals = annotations.get(filename, [])
#         y = create_labels(len(X), WINDOW_SIZE, theft_intervals)
#         all_X.append(X)
#         all_y.append(y)
#     X = np.concatenate(all_X)
#     y = np.concatenate(all_y)
#     return X, y

import os
import glob

import numpy as np
import pandas as pd

from src.preprocess import load_csv
from src.features import create_features
from src.windows import create_windows
from src.labels import create_labels

WINDOW_SIZE = 20

def load_annotations(path):
    annotations = {}
    df = pd.read_csv(path)
    for _, row in df.iterrows():
        filename = row["filename"]
        start = row["start"]
        end = row["end"]
        annotations.setdefault(filename, []).append((start, end))
    return annotations


def build_dataset(data_folder, annotations_file):
    """
    Retourne X, y, groups.
    `groups` associe chaque fenêtre à l'index de son fichier source, pour
    permettre un split train/test PAR FICHIER (voir train.py) et éviter
    toute fuite de données entre fenêtres qui se chevauchent.
    """
    annotations = load_annotations(annotations_file)
    all_X, all_y, all_groups = [], [], []
    csv_files = sorted(glob.glob(os.path.join(data_folder, "**", "*.csv"), recursive=True))
    for file_idx, csv_file in enumerate(csv_files):
        df = load_csv(csv_file)
        features = create_features(df)
        X = create_windows(features, WINDOW_SIZE)
        filename = os.path.basename(csv_file)
        theft_intervals = annotations.get(filename, [])
        y = create_labels(len(X), WINDOW_SIZE, theft_intervals)
        all_X.append(X)
        all_y.append(y)
        all_groups.append(np.full(len(X), file_idx))
    X = np.concatenate(all_X)
    y = np.concatenate(all_y)
    groups = np.concatenate(all_groups)
    return X, y, groups