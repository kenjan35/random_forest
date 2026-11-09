"""Pure helpers shared by background workers."""


def timestamp_sort_key(value):
    """Sort numeric epochs before textual ISO timestamps."""
    if isinstance(value, (int, float)):
        return (0, float(value), "")
    return (1, 0.0, str(value))


def xpath_literal(value):
    """Quote a value for use as an XPath string literal."""
    if "'" not in value:
        return f"'{value}'"
    if '"' not in value:
        return f'"{value}"'
    parts = value.split("'")
    return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"
