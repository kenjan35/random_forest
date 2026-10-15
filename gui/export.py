"""
Export CSV des évènements détectés, partagé par les onglets
"Analyser un fichier", "Scanner un dossier" et "Extraction Power-Noc".
"""

import csv
import os

COUNTRY = "MG"
THEFT_LABEL = "Fuel Theft"
GLITCH_LABEL = "Data incomplete"

CSV_HEADER = [
    "country", "mapping", "last_stable_date", "triggered_label",
    "event_id", "event_start", "total_loss", "rows_involved", "event_end",
]


def tagged_events(result):
    """[(évènement, libellé), ...] : vols d'abord, puis données incomplètes."""
    return (
        [(ev, THEFT_LABEL) for ev in result.get("events", [])]
        + [(ev, GLITCH_LABEL) for ev in result.get("events_ignored", [])]
    )


def event_list_label(event, label):
    """Texte affiché dans les listes de périodes de l'interface."""
    return f'{label} — Lignes {event["row_start"]}-{event["row_end"]}\n{event["ts_start"]}  →  {event["ts_end"]}'


def _event_rows(result, mapping):
    base_name = mapping[:-4] if mapping.lower().endswith(".csv") else mapping
    timestamps = result.get("timestamps")
    rows = []
    for index, (event, label) in enumerate(tagged_events(result), start=1):
        row_start, row_end = event["row_start"], event["row_end"]
        if timestamps is not None and row_start > 0:
            last_stable_date = str(timestamps[row_start - 1])
        else:
            last_stable_date = event["ts_start"]  # pas de relevé antérieur disponible
        rows.append([
            COUNTRY,
            mapping,
            last_stable_date,
            label,
            f"{base_name}_{index}",
            event["ts_start"],
            event.get("fuel_drop", 0.0),
            row_end - row_start + 1,
            event["ts_end"],
        ])
    return rows


def write_events_csv(path, results, mapping_key="filename"):
    """
    Écrit un CSV (une ligne par évènement) pour les résultats sans erreur.
    `mapping_key` : champ du résultat utilisé comme identifiant du site
    ("filename" pour les fichiers, "site" pour Power-Noc).
    Encodage utf-8-sig : les accents s'affichent correctement dans Excel.
    Lève OSError si le fichier ne peut pas être écrit (ex. ouvert dans Excel).
    """
    rows = []
    for result in results:
        if not result or result.get("error"):
            continue
        mapping = str(result.get(mapping_key) or os.path.basename(result.get("csv_path", "")))
        rows.extend(_event_rows(result, mapping))

    with open(path, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)
    return len(rows)
