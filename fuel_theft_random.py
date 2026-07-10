import pandas as pd
import numpy as np

def create_windows(dataframe, window_size) -> np.ndarray:
    windows = []
    for i in range(dataframe.size - window_size + 1):
        windows.append(dataframe[i:i + window_size])
    return np.array(windows)

df = pd.read_csv("Normal_1.csv")
print(df.columns)
print(df.head)
df = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"]
df = df.to_numpy()
print(type(df))
print(df)

print(create_windows(df, 5))