import numpy as np

def compute_delta(fuel):
    delta = fuel[1:] - fuel[:-1]
    delta = np.insert(delta, 0, 0)
    return delta

def create_features(fuel):
    delta = compute_delta(fuel)
    return np.column_stack((fuel, delta, np.abs(delta)))