"""Stateless helpers used by the RMS client."""

import os
import re
from datetime import timedelta


def normalize_endpoint(url):
    """Return an endpoint host and whether HTTPS should be used."""
    text = str(url or "").strip()
    secure = not text.lower().startswith("http://")
    host = re.sub(r"^https?://", "", text, flags=re.IGNORECASE).strip().rstrip("/")
    if not host or "/" in host:
        raise ValueError(
            "Point de terminaison invalide : indiquez seulement l'adresse du serveur, "
            "par exemple https://api-rms.appesca.com"
        )
    return host, secure


def env_credentials():
    return os.environ.get("RMS_ACCESS_KEY", ""), os.environ.get("RMS_SECRET_KEY", "")


def entry_name(key, prefix):
    """Return an object or directory name relative to its current prefix."""
    return key[len(prefix):].rstrip("/") if key.startswith(prefix) else key.rstrip("/")


def is_access_denied(exc):
    return getattr(exc, "code", None) == "AccessDenied"


def day_prefixes(country, start, end):
    """Return one bucket prefix for every day in the inclusive date range."""
    if end < start:
        start, end = end, start
    days = (end - start).days + 1
    return [f"{country}/{(start + timedelta(days=i)):%Y/%m/%d}/" for i in range(days)]
