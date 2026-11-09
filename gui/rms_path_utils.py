"""Safe local path helpers for RMS object keys."""

import os


def output_path(output_dir, key, decompress):
    """Build a local path while rejecting traversal components."""
    relative = key[:-3] if decompress and key.endswith(".gz") else key
    parts = [part for part in relative.split("/") if part]
    if any(part in ("..", ".") for part in parts):
        raise ValueError(f"Nom d'objet invalide : {key}")
    return os.path.join(output_dir, *parts)
