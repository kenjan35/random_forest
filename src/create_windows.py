import numpy as np

def create_windows(dataframe, window_size) -> np.ndarray:
    windows = []
    for i in range(dataframe.size - window_size + 1):
        windows.append(dataframe[i:i + window_size])
    return np.array(windows)