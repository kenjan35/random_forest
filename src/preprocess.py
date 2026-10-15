import pandas as pd

from src.config import FUEL_COL, STATUS_COL, TIME_COL


def clean_fuel(series):
    """
    Convertit la colonne carburant en float et comble les trous.
    Une valeur non numérique ou vide devient NaN, puis est interpolée
    linéairement (et complétée aux extrémités). Sans ça, un seul NaN se
    propage dans toutes les statistiques de fenêtre et dans les règles.
    Sur un fichier sans valeur manquante, le résultat est strictement
    identique à la colonne brute.
    """
    fuel = pd.to_numeric(series, errors="coerce").astype(float)
    if fuel.isna().any():
        fuel = fuel.interpolate(limit_direction="both")
        fuel = fuel.fillna(0.0)  # colonne entièrement vide
    return fuel.to_numpy()


def load_csv(file):
    """Retourne le volume de carburant (np.ndarray float) d'un export MFSX."""
    df = pd.read_csv(file, usecols=[FUEL_COL])
    return clean_fuel(df[FUEL_COL])


def load_site(file):
    """
    Lit en une seule passe ce dont la prédiction a besoin.
    Retourne (fuel, status, timestamps). `status` et `timestamps` valent
    None si la colonne correspondante est absente du fichier.
    """
    wanted = {FUEL_COL, STATUS_COL, TIME_COL}
    df = pd.read_csv(file, usecols=lambda c: c in wanted)
    if FUEL_COL not in df.columns:
        raise ValueError(f"Colonne carburant introuvable : {FUEL_COL!r}")

    fuel = clean_fuel(df[FUEL_COL])
    status = df[STATUS_COL].to_numpy() if STATUS_COL in df.columns else None
    timestamps = df[TIME_COL].to_numpy() if TIME_COL in df.columns else None
    return fuel, status, timestamps
