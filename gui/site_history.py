import os
import sqlite3
from datetime import datetime


DATABASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "site_history.db"
)

_schema_ready = False


def _connect():
    """Ouvre la base ; création/migration du schéma une seule fois par session."""
    global _schema_ready
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    if not _schema_ready:
        _ensure_schema(connection)
        _schema_ready = True
    return connection


def _ensure_schema(connection):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS site_history (
            site TEXT PRIMARY KEY,
            theft_count INTEGER NOT NULL DEFAULT 0,
            extraction_count INTEGER NOT NULL DEFAULT 0,
            fuel_loss REAL NOT NULL DEFAULT 0,
            last_seen TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS site_extractions (
            site TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            theft_count INTEGER NOT NULL DEFAULT 0,
            fuel_loss REAL NOT NULL DEFAULT 0,
            last_seen TEXT NOT NULL,
            PRIMARY KEY (site, period_start, period_end)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS theft_hours (
            site TEXT NOT NULL,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            event_index INTEGER NOT NULL,
            hour_bucket INTEGER NOT NULL,
            fuel_loss REAL NOT NULL DEFAULT 0,
            event_timestamp TEXT,
            PRIMARY KEY (site, period_start, period_end, event_index)
        )
        """
    )
    for table in ("site_history", "site_extractions"):
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if "fuel_loss" not in columns:
            connection.execute(
                f"ALTER TABLE {table} ADD COLUMN fuel_loss REAL NOT NULL DEFAULT 0"
            )
    theft_hour_columns = {row[1] for row in connection.execute("PRAGMA table_info(theft_hours)")}
    if "event_timestamp" not in theft_hour_columns:
        connection.execute("ALTER TABLE theft_hours ADD COLUMN event_timestamp TEXT")
    connection.commit()


def record_extraction(results, period_start, period_end):
    """Store successful extraction results and accumulate detected theft events."""
    now = datetime.now().isoformat(timespec="seconds")
    connection = _connect()
    try:
        for result in results:
            site = str(result.get("site") or "").strip()
            if not site or result.get("error"):
                continue
            theft_count = int(result.get("n_events") or 0)
            fuel_loss = sum(float(event.get("fuel_drop") or 0) for event in result.get("events", []))
            connection.execute(
                """
                INSERT INTO site_extractions
                    (site, period_start, period_end, theft_count, fuel_loss, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(site, period_start, period_end) DO UPDATE SET
                    theft_count = excluded.theft_count,
                    fuel_loss = excluded.fuel_loss,
                    last_seen = excluded.last_seen
                """,
                (site, period_start, period_end, theft_count, fuel_loss, now),
            )
            connection.execute(
                "DELETE FROM theft_hours WHERE site = ? AND period_start = ? AND period_end = ?",
                (site, period_start, period_end),
            )
            for event_index, event in enumerate(result.get("events", [])):
                timestamp = str(event.get("ts_start") or "").replace("Z", "+00:00")
                try:
                    hour_bucket = datetime.fromisoformat(timestamp).hour
                except ValueError:
                    continue
                connection.execute(
                    """
                    INSERT INTO theft_hours
                        (site, period_start, period_end, event_index, hour_bucket, fuel_loss, event_timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        site, period_start, period_end, event_index, hour_bucket,
                        float(event.get("fuel_drop") or 0), timestamp,
                    ),
                )
        connection.commit()
    finally:
        connection.close()


def get_top_theft_hours(limit=5):
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT hour_bucket, COUNT(*) AS theft_count, SUM(fuel_loss) AS total_fuel_loss
            FROM (
                SELECT site, hour_bucket, MAX(fuel_loss) AS fuel_loss
                FROM theft_hours
                GROUP BY site, hour_bucket
            ) AS unique_site_hours
            GROUP BY hour_bucket
            ORDER BY theft_count DESC, hour_bucket
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def get_theft_hour_points():
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT event_timestamp, hour_bucket, fuel_loss, site
            FROM theft_hours
            WHERE event_timestamp IS NOT NULL AND event_timestamp != ''
            ORDER BY event_timestamp
            """
        ).fetchall()
    finally:
        connection.close()


def get_theft_daily_points():
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT substr(event_timestamp, 1, 10) AS event_day,
                   COUNT(*) AS theft_count, SUM(fuel_loss) AS fuel_loss
            FROM theft_hours
            WHERE event_timestamp IS NOT NULL AND event_timestamp != ''
            GROUP BY event_day
            ORDER BY event_day
            """
        ).fetchall()
    finally:
        connection.close()


def get_recent_theft_events(limit=20):
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT site, event_timestamp, fuel_loss
            FROM theft_hours
            WHERE event_timestamp IS NOT NULL AND event_timestamp != ''
            ORDER BY event_timestamp DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def get_top_sites(limit=5):
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT site, SUM(theft_count) AS total_theft_count,
                   SUM(fuel_loss) AS total_fuel_loss, COUNT(*), MAX(last_seen)
            FROM (
                SELECT site, theft_count, fuel_loss, extraction_count AS extraction_count, last_seen
                FROM site_history
                UNION ALL
                SELECT site, theft_count, fuel_loss, 1 AS extraction_count, last_seen
                FROM site_extractions
            )
            WHERE theft_count > 0
            GROUP BY site
            ORDER BY total_theft_count DESC, last_seen DESC, site COLLATE NOCASE
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        connection.close()


def get_dashboard_summary():
    connection = _connect()
    try:
        return connection.execute(
            """
            SELECT COUNT(DISTINCT site), COALESCE(SUM(theft_count), 0),
                   COALESCE(SUM(fuel_loss), 0)
            FROM (
                SELECT site, theft_count, fuel_loss FROM site_history
                UNION ALL
                SELECT site, theft_count, fuel_loss FROM site_extractions
            )
            WHERE theft_count > 0
            """
        ).fetchone()
    finally:
        connection.close()