"""Helpers de construction et de classification des événements d'analyse."""

import numpy as np

from gui.analysis_utils import (
    GLITCH_OVERLAP_THRESHOLD,
    group_consecutive,
)
from gui.fuel_math import event_loss
from src.predict import WINDOW_SIZE


def make_event(fuel, timestamps, row_start, row_end, glitch_ratio=0.0, fuel_drop=None):
    row_start, row_end = int(row_start), int(row_end)
    event = {
        "row_start": row_start,
        "row_end": row_end,
        "ts_start": str(timestamps[row_start]),
        "ts_end": str(timestamps[row_end]),
        "glitch_ratio": round(float(glitch_ratio), 2),
        "fuel_drop": event_loss(fuel, row_start, row_end),
    }
    if fuel_drop is not None:
        event["fuel_drop"] = fuel_drop
    return event


def overlapping_bridge(bridged, row_start, row_end):
    return next(
        (bridge for bridge in bridged
         if bridge["start"] <= row_end and bridge["end"] >= row_start),
        None,
    )


def append_unreported_glitches(events, glitch_mask, bridged, fuel, timestamps):
    covered = [(event["row_start"], event["row_end"]) for event in events]
    for start, end in group_consecutive(np.flatnonzero(glitch_mask)):
        if overlapping_bridge(bridged, start, end) is not None:
            continue
        if not any(row_start <= start and end <= row_end
                   for row_start, row_end in covered):
            events.append(make_event(fuel, timestamps, start, end, 1.0))


def classify_events(prediction, glitch_mask, bridged, fuel, timestamps):
    """Construit les événements détectés et ceux écartés pour décrochage capteur."""
    n_rows = len(fuel)
    events, events_ignored = [], []

    for window_start, window_end in group_consecutive(np.flatnonzero(prediction == 1)):
        row_start = window_start
        row_end = min(window_end + WINDOW_SIZE - 1, n_rows - 1)
        glitch_ratio = float(glitch_mask[row_start:row_end + 1].mean())
        bridge = overlapping_bridge(bridged, row_start, row_end)
        event = make_event(fuel, timestamps, row_start, row_end, glitch_ratio)
        if bridge is not None:
            event["fuel_drop"] = bridge["loss"]
            event["zero_bridged"] = True
            events.append(event)
        elif glitch_ratio >= GLITCH_OVERLAP_THRESHOLD:
            events_ignored.append(event)
        else:
            events.append(event)

    append_unreported_glitches(events_ignored, glitch_mask, bridged, fuel, timestamps)
    events_ignored.sort(key=lambda event: event["row_start"])
    return events, events_ignored