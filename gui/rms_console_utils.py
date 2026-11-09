"""Pure formatting helpers for the RMS console."""


def download_text(stats, format_size):
    """Format download progress without depending on widgets."""
    done = stats["telecharges"] + stats["deja_presents"]
    rate = done / max(stats.get("duree", 0), 0.1)
    listed = f"{stats['listes']:,}" + ("" if stats["listage_termine"] else "+")
    parts = [
        f"{done:,} / {listed} fichiers",
        f"{rate:.0f} fichiers/s",
        format_size(stats["octets"]),
    ]
    if stats.get("sites"):
        parts.append(f"{stats['sites']:,} mapping(s)")
    if stats["deja_presents"]:
        parts.append(f"{stats['deja_presents']:,} déjà présents")
    if stats["erreurs"]:
        parts.append(f"{stats['erreurs']:,} erreur(s)")
    if stats["listage_termine"] and rate > 0:
        remaining = (stats["listes"] - done - stats["erreurs"]) / rate
        if remaining > 1:
            parts.append(f"reste ~{int(remaining // 60)} min {int(remaining % 60):02d} s")
    return " · ".join(parts).replace(",", " ")
