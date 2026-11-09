"""Helpers for converting RMS listing entries to UI records."""

from gui.rms_client_utils import entry_name


def to_entry(item, prefix):
    key = str(item.object_name)
    is_dir = bool(getattr(item, "is_dir", False)) or key.endswith("/")
    modified = getattr(item, "last_modified", None)
    return {
        "key": key,
        "name": entry_name(key, prefix),
        "is_dir": is_dir,
        "size": None if is_dir else int(getattr(item, "size", 0) or 0),
        "modified": modified.astimezone().replace(tzinfo=None) if modified else None,
    }
