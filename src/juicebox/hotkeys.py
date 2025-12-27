"""Hotkey definitions for Juicebox application.

q - Quit the app.
? - Show help screen.
WASD - Move around.
r, F5, Ctrl+R - Refresh the page.
Ctrl+E - Enter a new URL.
Ctrl+F - Search in page.
Ctrl+Shift+F - Search in all tabs.
Ctrl+T - Open new tab.
Ctrl+W - Close current tab.
Ctrl+PageUp / Ctrl+PageDown or Alt+Z / Alt+X - Switch tabs.
Ctrl+L - Toggle theme.
"""

from textual.binding import Binding
from textual.binding import BindingType


def get_hotkeys() -> list[BindingType]:
    """Get the list of hotkeys for the application.

    Returns:
        list[BindingType]: A list of hotkey bindings.
    """
    return [
        Binding(
            key="q",
            action="quit",
            description="Quit the app",
            priority=True,
        ),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
            priority=True,
        ),
        #
        # Move around with WASD
        Binding(
            key="w",
            action="up",
            description="Scroll up",
            tooltip="Scroll up",
        ),
        Binding(
            key="s",
            action="down",
            description="Scroll down",
            tooltip="Scroll down",
        ),
        Binding(
            key="a",
            action="left",
            description="Go left",
            tooltip="Go left",
        ),
        Binding(
            key="d",
            action="right",
            description="Go right",
            tooltip="Go right",
        ),
        #
        # Refresh with r, ctrl+r or F5
        # Binding(
        #     key="r",
        #     action="refresh",
        #     description="Refresh the page",
        #     show=False,
        # ),
        # Binding(
        #     key="f5",
        #     action="refresh",
        #     description="Refresh the page",
        #     show=False,
        # ),
        # Binding(
        #     key="ctrl+r",
        #     action="refresh",
        #     description="Refresh the page",
        #     priority=True,
        # ),
        #
        # URL entry
        Binding(
            key="ctrl+e",
            action="open_url",
            description="Enter a new URL",
            priority=True,
        ),
        #
        # Search within page
        # Binding(
        #     key="ctrl+f",
        #     action="search",
        #     description="Search in page",
        #     priority=True,
        # ),
        # #
        # # Search within all tabs
        # Binding(
        #     key="ctrl+shift+f",
        #     action="search",
        #     description="Search in all tabs",
        #     priority=True,
        # ),
        #
        # Tab management
        Binding(
            key="ctrl+t",
            action="new_tab",
            description="Open new tab",
            priority=True,
        ),
        Binding(
            key="ctrl+w",
            action="close_tab",
            description="Close current tab",
            priority=True,
        ),
        Binding(
            key="ctrl+pageup",
            action="previous_tab",
            description="Previous tab",
            priority=True,
        ),
        Binding(
            key="ctrl+pagedown",
            action="next_tab",
            description="Next tab",
            priority=True,
        ),
        Binding(
            key="alt+z",
            action="previous_tab",
            description="Previous tab",
            priority=True,
        ),
        Binding(
            key="alt+x",
            action="next_tab",
            description="Next tab",
            priority=True,
        ),
        #
        # Theme toggle
        Binding(
            key="ctrl+l",
            action="toggle_theme",
            description="Toggle theme",
            priority=True,
        ),
        #
        # Image rendering method toggle
        Binding(
            key="ctrl+i",
            action="toggle_image_method",
            description="Toggle image rendering",
            priority=True,
        ),
    ]
