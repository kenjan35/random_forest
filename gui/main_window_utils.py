"""Stateless helpers used by the main application window."""

import os

from PySide6.QtGui import QIcon


def update_sidebar_icons(buttons, selected_index, dark_mode=False):
    """Apply the appropriate icon to each sidebar button."""
    for index, button in enumerate(buttons):
        icon_name = (
            button.selected_icon
            if index == selected_index or dark_mode
            else button.default_icon
        )
        button.setIcon(QIcon(os.path.join("assets", "icons", icon_name)))


def select_view(stack, buttons, index):
    """Select a stacked view and keep its buttons synchronized."""
    stack.setCurrentIndex(index)
    for button_index, button in enumerate(buttons):
        button.setChecked(button_index == index)
