"""User-facing error formatting for RMS requests."""

import re


_CLOUDFLARE_STATUS = {
    520: "le serveur de stockage a renvoyé une réponse inattendue",
    521: "le serveur de stockage refuse la connexion (service arrêté ?)",
    522: "le serveur de stockage ne répond pas (délai de connexion dépassé)",
    523: "le serveur de stockage est injoignable depuis Cloudflare",
    524: "le serveur de stockage a mis trop de temps à répondre",
    525: "échec de la négociation SSL avec le serveur de stockage",
    526: "certificat SSL du serveur de stockage invalide",
    530: "Cloudflare n'arrive pas à joindre le serveur de stockage",
}
_CLOUDFLARE_CODES = {
    "1016": "nom DNS du serveur introuvable",
    "1033": "le tunnel Cloudflare vers le serveur est arrêté",
}
_S3_MESSAGES = {
    "InvalidAccessKeyId": "Clé d'accès invalide ou inconnue.",
    "SignatureDoesNotMatch": "Clé secrète incorrecte.",
    "AccessDenied": "Accès refusé : vos droits ne permettent pas de lister ou lire cet emplacement.",
    "NoSuchBucket": "Ce bucket n'existe pas ou ne vous est pas accessible.",
    "NoSuchKey": "Ce fichier n'existe plus.",
    "RequestTimeTooSkewed": "L'horloge de votre ordinateur est décalée : remettez-la à l'heure puis réessayez.",
}


def describe_http_error(exc, endpoint="api-rms.appesca.com"):
    text = str(exc)
    status = getattr(exc, "_code", None) or getattr(exc, "status_code", None)
    if status is None:
        match = re.search(r"Response code:\s*(\d{3})", text)
        status = match.group(1) if match else None
    if status is None or ("non-XML" not in text and not str(status).startswith("5")):
        return None
    status = int(status)
    if status < 500:
        return None
    cause = _CLOUDFLARE_STATUS.get(status, "erreur côté serveur")
    cf_match = re.search(r"(?:error code:?|Error)\s*(1\d{3})", text, re.IGNORECASE)
    if cf_match:
        cf_code = cf_match.group(1)
        detail = f" : {_CLOUDFLARE_CODES[cf_code]}" if cf_code in _CLOUDFLARE_CODES else ""
        cause += f" (Cloudflare {cf_code}{detail})"
    return (f"Le serveur {endpoint} est indisponible (HTTP {status}) : {cause}.\n\n"
            "Vos clés d'accès ne sont pas en cause : la requête n'a pas atteint le stockage.\n"
            "Réessayez plus tard ou prévenez l'équipe BIG DATA & AI.")


def error_message(exc, endpoint="api-rms.appesca.com"):
    code = getattr(exc, "code", None)
    if code in _S3_MESSAGES:
        return _S3_MESSAGES[code]
    http = describe_http_error(exc, endpoint)
    if http:
        return http
    name = type(exc).__name__
    if name in ("MaxRetryError", "NewConnectionError", "ConnectionError", "NameResolutionError") \
            or "Max retries exceeded" in str(exc):
        return (f"Impossible de joindre {endpoint}. Vérifiez votre connexion Internet "
                "et l'adresse du point de terminaison.")
    if isinstance(exc, ValueError):
        return str(exc)
    if code:
        return f"Erreur S3 ({code}) : {getattr(exc, 'message', '') or exc}"
    return f"{name} : {exc}"
