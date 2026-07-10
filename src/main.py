from create_windows import create_windows
from preprocess import load_csv
from features import create_features
import numpy as np

df = load_csv()

X = create_features(df)
y = np.zeros(50, dtype=int)

windows = create_windows(df, 5)
print(windows)

