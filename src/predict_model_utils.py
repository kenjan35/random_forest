import os
from functools import lru_cache
import joblib
from src.predict import MODEL_PATH, THRESHOLD_PATH, DEFAULT_THRESHOLD

def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return None


@lru_cache(maxsize=1)
def _load_model_cached(model_mtime, threshold_mtime):
    model = joblib.load(MODEL_PATH)
    threshold = float(joblib.load(THRESHOLD_PATH)) if threshold_mtime is not None else DEFAULT_THRESHOLD
    return model, threshold


def load_model():
    """Retourne (modèle, seuil). Le disque n'est relu que si les fichiers ont changé."""
    model_mtime = _mtime(MODEL_PATH)
    if model_mtime is None:
        raise FileNotFoundError(f"Modèle introuvable : {MODEL_PATH}")
    return _load_model_cached(model_mtime, _mtime(THRESHOLD_PATH))

