"""Helpers sans état pour l'analyse des fichiers de carburant."""

import glob
import os

import numpy as np
import pandas as pd

from src.predict import (
    GLITCH_REFERENCE_FRACTION,
    confirmed_glitch_mask,
)

TANK_VOLUME_COLUMN = "(MFSX) FSA Total Tank Volume (Ltr) [MFSX:01:1:6] (S1)"
GLITCH_OVERLAP_THRESHOLD = 0.6
GLITCH_BASELINE_RATIO = GLITCH_REFERENCE_FRACTION


def group_consecutive(indices):
    """Regroupe des indices triés en intervalles consécutifs."""
    indices = np.asarray(indices, dtype=np.int64)
    if len(indices) == 0:
        return []
    breaks = np.flatnonzero(np.diff(indices) != 1)
    starts = np.concatenate(([indices[0]], indices[breaks + 1]))
    ends = np.concatenate((indices[breaks], [indices[-1]]))
    return list(zip(starts.tolist(), ends.tolist()))


def find_csv_files(folder):
    return sorted(glob.glob(os.path.join(folder, "**", "*.csv"), recursive=True))


def detect_sensor_glitches(fuel):
    """
    Retourne les coupures capteur confirmées, y compris au début du fichier.
    """
    return confirmed_glitch_mask(fuel, include_leading=True)


def read_tank_capacity(df):
    if TANK_VOLUME_COLUMN not in df.columns:
        return None
    values = pd.to_numeric(df[TANK_VOLUME_COLUMN], errors="coerce").dropna()
    return float(values.median()) if not values.empty else None
