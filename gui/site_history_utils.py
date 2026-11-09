"""Pure value preparation for the site-history persistence layer."""

from datetime import datetime


def event_timestamp(event):
    return str(event.get("ts_start") or "").replace("Z", "+00:00")


def event_hour(event):
    try:
        return datetime.fromisoformat(event_timestamp(event)).hour
    except ValueError:
        return None


def fuel_loss(events):
    return sum(float(event.get("fuel_drop") or 0) for event in events)


def result_site(result):
    return str(result.get("site") or "").strip()
