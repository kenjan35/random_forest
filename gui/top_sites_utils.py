"""Stateless helpers for the dashboard tables."""

from datetime import datetime


def parse_timestamp(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=None)


def fit_table_height(table):
    visible_rows = min(max(table.rowCount(), 1), 5)
    return (
        table.horizontalHeader().height()
        + visible_rows * table.verticalHeader().defaultSectionSize()
        + 2 * table.frameWidth()
    )
