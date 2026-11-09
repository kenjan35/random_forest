"""Pure path helpers for storage downloads."""

import os
from pathlib import Path


def safe_destination(output_dir, object_name):
    """Return a destination below output_dir, rejecting traversal."""
    output_root = Path(output_dir).resolve()
    relative_name = Path(object_name.replace("/", os.sep))
    if relative_name.is_absolute() or ".." in relative_name.parts:
        raise ValueError(f"Nom d'objet invalide : {object_name}")
    destination = (output_root / relative_name).resolve()
    if output_root not in destination.parents:
        raise ValueError(f"Chemin de téléchargement invalide : {object_name}")
    return output_root, destination
