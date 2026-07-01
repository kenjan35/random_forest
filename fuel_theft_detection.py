"""Fuel theft detection data preparation and baseline anomaly model.

This script:
1. Loads a CSV file with columns like:
   - Time stamp
   - FSA Fuel Volume (Ltr)
   - FSA Generator Running
2. Cleans and parses the data.
3. Creates basic time-series features.
4. Fits a simple anomaly detection model.
5. Saves scored output to a new CSV.

Usage:
    python fuel_theft_detection.py --input TATS086.csv --output scored.csv
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


TIME_COL_CANDIDATES = ["Time stamp", "Time", "Timestamp", "time_stamp"]
FUEL_COL_CANDIDATES = [
    "(MFSX) FSA Fuel Volume (Ltr) [MFSX:01:1:4] (S1)",
    "FSA Fuel Volume (Ltr)",
    "Fuel Volume",
    "fuel_volume",
]
GEN_COL_CANDIDATES = [
    "FSA Generator Running [MFSX:01:1:12] (S2)",
    "Generator Running",
    "generator_running",
]


@dataclass
class ColumnMap:
    time: str
    fuel: str
    generator: str


def _pick_column(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def infer_columns(df: pd.DataFrame) -> ColumnMap:
    time_col = _pick_column(df, TIME_COL_CANDIDATES)
    fuel_col = _pick_column(df, FUEL_COL_CANDIDATES)
    gen_col = _pick_column(df, GEN_COL_CANDIDATES)

    if not time_col or not fuel_col or not gen_col:
        raise ValueError(
            "Could not infer required columns. Found columns: "
            f"{list(df.columns)}"
        )

    return ColumnMap(time=time_col, fuel=fuel_col, generator=gen_col)


def parse_generator(value: object) -> float:
    if pd.isna(value):
        return np.nan
    text = str(value).strip().lower()
    if "active" in text or re.search(r"\b1\b", text):
        return 1.0
    if "inactive" in text or re.search(r"\b0\b", text):
        return 0.0
    return np.nan


def load_and_prepare(csv_path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    cols = infer_columns(df)

    out = pd.DataFrame()
    out["timestamp"] = pd.to_datetime(df[cols.time], errors="coerce", dayfirst=True)
    out["fuel_volume"] = pd.to_numeric(df[cols.fuel], errors="coerce")
    out["generator_running"] = df[cols.generator].apply(parse_generator)

    out = out.dropna(subset=["timestamp", "fuel_volume", "generator_running"])
    out = out.sort_values("timestamp").reset_index(drop=True)

    # Basic time-series features
    out["fuel_volume_prev"] = out["fuel_volume"].shift(1)
    out["fuel_volume_change"] = out["fuel_volume"] - out["fuel_volume_prev"]
    out["abs_fuel_volume_change"] = out["fuel_volume_change"].abs()

    # Time delta in minutes between rows
    out["delta_minutes"] = (
        out["timestamp"].diff().dt.total_seconds().div(60.0)
    )
    out["delta_minutes"] = out["delta_minutes"].fillna(0.0)

    out["fuel_change_rate_per_min"] = np.where(
        out["delta_minutes"] > 0,
        out["fuel_volume_change"] / out["delta_minutes"],
        0.0,
    )

    # Rolling context
    out["fuel_volume_roll_mean_6"] = out["fuel_volume"].rolling(6, min_periods=1).mean()
    out["fuel_volume_roll_std_6"] = out["fuel_volume"].rolling(6, min_periods=1).std().fillna(0.0)
    out["fuel_volume_deviation_6"] = out["fuel_volume"] - out["fuel_volume_roll_mean_6"]

    # Generator context
    out["generator_prev"] = out["generator_running"].shift(1).fillna(out["generator_running"])
    out["generator_change"] = out["generator_running"] - out["generator_prev"]

    # Suspicion-oriented features
    out["drop_while_inactive"] = np.where(
        (out["generator_running"] == 0) & (out["fuel_volume_change"] < 0),
        out["fuel_volume_change"],
        0.0,
    )
    out["drop_while_active"] = np.where(
        (out["generator_running"] == 1) & (out["fuel_volume_change"] < 0),
        out["fuel_volume_change"],
        0.0,
    )

    # Clean up infinities / NaNs from early rows
    out = out.replace([np.inf, -np.inf], np.nan)
    out = out.dropna(subset=["fuel_volume_prev", "fuel_volume_change"])

    return out


def train_anomaly_model(df: pd.DataFrame) -> tuple[Pipeline, np.ndarray]:
    feature_cols = [
        "fuel_volume",
        "fuel_volume_change",
        "abs_fuel_volume_change",
        "delta_minutes",
        "fuel_change_rate_per_min",
        "fuel_volume_roll_mean_6",
        "fuel_volume_roll_std_6",
        "fuel_volume_deviation_6",
        "generator_running",
        "generator_change",
        "drop_while_inactive",
        "drop_while_active",
    ]

    X = df[feature_cols].fillna(0.0).astype(float)

    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "iso",
                IsolationForest(
                    n_estimators=200,
                    contamination="auto",
                    random_state=42,
                ),
            ),
        ]
    )

    model.fit(X)
    raw_pred = model.predict(X)  # 1 = normal, -1 = anomaly
    anomaly_score = -model.decision_function(X)

    return model, np.column_stack([raw_pred, anomaly_score])


def score_data(df: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "fuel_volume",
        "fuel_volume_change",
        "abs_fuel_volume_change",
        "delta_minutes",
        "fuel_change_rate_per_min",
        "fuel_volume_roll_mean_6",
        "fuel_volume_roll_std_6",
        "fuel_volume_deviation_6",
        "generator_running",
        "generator_change",
        "drop_while_inactive",
        "drop_while_active",
    ]

    X = df[feature_cols].fillna(0.0).astype(float)

    pipeline = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "iso",
                IsolationForest(
                    n_estimators=200,
                    contamination="auto",
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(X)

    df = df.copy()
    df["anomaly_flag"] = pipeline.predict(X)
    df["anomaly_flag"] = df["anomaly_flag"].map({1: 0, -1: 1}).astype(int)
    df["anomaly_score"] = -pipeline.decision_function(X)

    # A simple rule-based suspicion signal for quick inspection
    df["rule_suspicious"] = (
        (df["generator_running"] == 0)
        & (df["fuel_volume_change"] <= df["fuel_volume_change"].quantile(0.05))
    ).astype(int)

    df["final_suspicion"] = ((df["anomaly_flag"] == 1) | (df["rule_suspicious"] == 1)).astype(int)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Fuel theft detection baseline model")
    parser.add_argument("--input", required=True, help="Path to the input CSV file")
    parser.add_argument(
        "--output",
        default="scored_fuel_theft_output.csv",
        help="Path to save the scored CSV",
    )
    args = parser.parse_args()

    prepared = load_and_prepare(args.input)
    scored = score_data(prepared)

    out_path = Path(args.output)
    scored.to_csv(out_path, index=False)

    suspicious_count = int(scored["final_suspicion"].sum())
    total = len(scored)
    print(f"Saved: {out_path}")
    print(f"Rows processed: {total}")
    print(f"Suspicious rows: {suspicious_count}")


if __name__ == "__main__":
    main()
