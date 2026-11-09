"""Helpers internes de rendu du spinner."""


def replace_rect(match, state):
    opacity = "1" if state["index"] == state["active"] else "0.2"
    state["index"] += 1
    return f'<rect{match.group(1)} opacity="{opacity}">'
