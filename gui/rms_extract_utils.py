"""Helpers for producing the RMS extraction index."""


def index_row(key, parsed, status, path=""):
    parsed = parsed if isinstance(parsed, dict) else {}
    records = parsed.get("data") if isinstance(parsed.get("data"), list) else []
    stamps = sorted(str(record.get("Timestamp")) for record in records
                    if isinstance(record, dict) and record.get("Timestamp"))
    return {
        "key": key, "mapping": parsed.get("mapping", ""), "siteId": parsed.get("siteId", ""),
        "ingester": parsed.get("ingester", ""), "mesures": len(records),
        "debut": stamps[0] if stamps else "", "fin": stamps[-1] if stamps else "",
        "statut": status, "fichier_local": path,
    }
