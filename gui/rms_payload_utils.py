"""Formatting and decoding helpers for RMS payloads."""

import gzip
import json
from datetime import datetime


def decode_payload(raw):
    """Decompress (when needed) and pretty-print a JSON payload."""
    data = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    text = data.decode("utf-8", errors="replace")
    try:
        parsed = json.loads(text)
    except ValueError:
        return text, None
    return json.dumps(parsed, indent=2, ensure_ascii=False), parsed


def payload_summary(parsed):
    """Return a short human-readable summary of an RMS JSON payload."""
    if not isinstance(parsed, dict):
        return ""
    parts = [str(parsed[key]) for key in ("mapping", "siteId", "ingester") if parsed.get(key)]
    records = parsed.get("data")
    if isinstance(records, list):
        parts.append(f"{len(records)} mesure{'s' if len(records) > 1 else ''}")
        stamps = sorted(str(r.get("Timestamp")) for r in records
                        if isinstance(r, dict) and r.get("Timestamp"))
        if stamps:
            parts.append(stamps[0].replace("T", " ") if len(stamps) == 1
                         else f"{stamps[0].replace('T', ' ')} → {stamps[-1].replace('T', ' ')}")
    return " · ".join(parts)


def format_size(size):
    if size is None:
        return ""
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024


def format_date(value):
    return value.strftime("%d/%m/%Y %H:%M") if isinstance(value, datetime) else ""


def payload_mapping(data):
    """Return the mapping field from decompressed JSON bytes."""
    try:
        parsed = json.loads(data.decode("utf-8", errors="replace"))
    except ValueError:
        return ""
    return str(parsed.get("mapping") or "").strip() if isinstance(parsed, dict) else ""
