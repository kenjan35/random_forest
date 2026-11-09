"""Pure value-formatting helpers used by :mod:`gui.pdf_reports`."""

import re
from datetime import datetime


MONTHS_FR = (
    "JANVIER", "FEVRIER", "MARS", "AVRIL", "MAI", "JUIN",
    "JUILLET", "AOUT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE",
)


def safe_filename(value):
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", str(value).strip()).strip("_")
    return normalized or "SITE"


def period_label(start_date):
    try:
        parsed = datetime.strptime(start_date, "%Y-%m-%d")
        return f"{MONTHS_FR[parsed.month - 1]} {parsed.year}"
    except (TypeError, ValueError):
        return str(start_date or "PERIODE").upper()


def event_date(event):
    value = str(event.get("ts_start", ""))
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    return parsed.strftime("%d/%m/%Y") if parsed else value[:10]


def event_time(value):
    """Return HH:MM regardless of seconds, milliseconds, or a ``Z`` suffix."""
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        parsed = None
    return parsed.strftime("%H:%M") if parsed else str(value)[-8:-3]


def event_time_range(event):
    return f"{event_time(event.get('ts_start', ''))} - {event_time(event.get('ts_end', ''))}"
