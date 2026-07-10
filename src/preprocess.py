import pandas as pd

def load_csv():
    df = pd.read_csv("data/normal/Normal_1.csv")
    df = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"]
    df = df.to_numpy()
    return df