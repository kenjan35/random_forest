# Old version of mine
#  from windows import create_windows
# from preprocess import load_csv
# from features import create_features
# from labels import create_labels
# import numpy as np
# import json

# with open("annotations.json", "r") as f:
#     annotations = json.load(f)

# window_size = 5

# df_normal = load_csv("data/normal/Normal_1.csv")
# df_theft = load_csv("data/theft/Theft_1.csv")

# X_normal = create_features(df_normal)
# y_normal = np.zeros(50, dtype=int)

# X_theft = create_features(df_theft)
# y_theft = create_labels(len(X_theft), window_size, )

# windows = create_windows(df_normal, window_size)
# print(windows)


# Second version with CGPT
# from src.dataset import build_dataset
# from src.train import train

# DATA_FOLDER = "data"

# ANNOTATIONS = "annotations.csv"

# X, y = build_dataset(
#     DATA_FOLDER,
#     ANNOTATIONS
# )

# print(X.shape)

# print(y.shape)

# train(X, y)

# import numpy as np
# from src.dataset import build_dataset

# X, y = build_dataset("data", "annotations.csv")
# vals, counts = np.unique(y, return_counts=True)
# print(X.shape, dict(zip(vals.tolist(), counts.tolist())))

from src.dataset import build_dataset
from src.train import train

DATA_FOLDER = "data"
ANNOTATIONS = "annotations.csv"

X, y, groups = build_dataset(
    DATA_FOLDER,
    ANNOTATIONS
)

print(X.shape)
print(y.shape)

train(X, y, groups)