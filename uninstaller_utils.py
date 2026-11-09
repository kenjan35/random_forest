"""Pure PowerShell string helpers for the uninstaller."""


def ps_quote(text):
    return "'" + str(text).replace("'", "''") + "'"
