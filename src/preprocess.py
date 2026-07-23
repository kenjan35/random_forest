import pandas as pd

def load_csv(file):
    df = pd.read_csv(file)
    df = df["(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)"]
    df = df.to_numpy()
    return df