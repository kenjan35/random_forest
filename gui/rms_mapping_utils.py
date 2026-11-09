"""Mapping and output-name helpers for RMS downloads."""

import os
import re
import unicodedata


NO_MAPPING_FOLDER = "_sans_mapping"
_INVALID_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_DAY_PATH = re.compile(r"(?:^|/)(\d{4})/(\d{2})/(\d{2})/")


def parse_mappings(text):
    """Parse comma, semicolon, or whitespace-separated mapping codes."""
    codes = []
    for code in re.split(r"[\s,;]+", str(text or "")):
        code = code.strip().upper()
        if code and code not in codes:
            codes.append(code)
    return codes


def mapping_folder_name(mapping):
    """Return a safe Windows folder name for a mapping code."""
    name = _INVALID_NAME.sub("_", str(mapping or "")).strip().rstrip(". ")
    return name or NO_MAPPING_FOLDER


def sorted_file_name(key):
    """Return a date-prefixed JSON filename for a bucket key."""
    name = key.rsplit("/", 1)[-1]
    if name.endswith(".gz"):
        name = name[:-3]
    if not name.endswith(".json"):
        name += ".json"
    day = _DAY_PATH.search(key)
    return f"{day.group(1)}-{day.group(2)}-{day.group(3)}_{name}" if day else name


def existing_sorted_files(output_dir):
    """Return names of files already extracted in mapping/site folders."""
    names = set()
    try:
        folders = [entry for entry in os.scandir(output_dir) if entry.is_dir()]
    except OSError:
        return names
    for folder in folders:
        try:
            names.update(entry.name for entry in os.scandir(folder.path) if entry.is_file())
        except OSError:
            continue
    return names


def read_mappings_from_excel(path):
    """Read unique mapping codes from the first matching Excel column."""
    from openpyxl import load_workbook

    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        cell = next((c for row in sheet.iter_rows(min_row=1, max_row=30) for c in row
                     if c.value is not None and
                     unicodedata.normalize("NFKC", str(c.value)).replace("\ufeff", "").replace("\xa0", " ").strip().casefold() == "mapping"), None)
        if cell is None:
            raise ValueError("La colonne 'mapping' est introuvable dans les 30 premières lignes.")
        codes = []
        for (value,) in sheet.iter_rows(min_row=cell.row + 1, min_col=cell.column,
                                        max_col=cell.column, values_only=True):
            code = str(value).strip().upper() if value is not None else ""
            if code and code not in codes:
                codes.append(code)
        return codes
    finally:
        workbook.close()
