import pandas as pd
import numpy as np

df = pd.read_csv("Normal_1.csv")
print(df.columns)
print(df.head)
df = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"]
df = df.to_numpy()
print(type(df))

windows = np.array([])

for i in df:
    windows[i] = df[i:df.size]