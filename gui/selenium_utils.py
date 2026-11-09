"""Stateless value formatting helpers for the Selenium extraction tab."""

from datetime import datetime
import unicodedata


def format_alert_timestamp(value):
    text = str(value or "").strip()
    for format_string in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text.rstrip("Z"), format_string).strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return text[:16]


def alert_range(events):
    if not events:
        return "", ""
    return format_alert_timestamp(events[0].get("ts_start")), format_alert_timestamp(events[-1].get("ts_end"))


def total_loss(events):
    return f"{sum(float(event.get('fuel_drop') or 0) for event in events):.1f} L"


def format_capacity(value):
    if value is None or value == "":
        return ""
    return f"{float(value):.1f} L"


def normalize_excel_value(value):
    text = unicodedata.normalize("NFKC", str(value))
    return text.replace("\ufeff", "").replace("\xa0", " ").strip().casefold()
