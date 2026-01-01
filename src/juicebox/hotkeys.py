from textual.binding import Binding
from textual.binding import BindingType


def get_hotkeys() -> list[BindingType]:
    """Get the list of hotkeys for the application.

    Returns:
        list[BindingType]: A list of hotkey bindings.
    """
    return [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="question_mark", action="help", description="Show help screen", key_display="?"),
        #
        # Move around with WASD
        Binding(key="w", action="up", description="Scroll up", tooltip="Scroll up"),
        Binding(key="s", action="down", description="Scroll down", tooltip="Scroll down"),
        Binding(key="a", action="left", description="Go left", tooltip="Go left"),
        Binding(key="d", action="right", description="Go right", tooltip="Go right"),
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
        #
        # ),
        #
        # URL entry
        Binding(key="ctrl+e", action="open_url", description="Enter a new URL"),
        #
        # Search within page
        # Binding(
        #     key="ctrl+f",
        #     action="search",
        #     description="Search in page",
        #
        # ),
        # #
        # # Search within all tabs
        # Binding(
        #     key="ctrl+shift+f",
        #     action="search",
        #     description="Search in all tabs",
        #
        # ),
        #
        # Tab management
        Binding(key="ctrl+t", action="new_tab", description="Open new tab"),
        Binding(key="ctrl+w", action="close_tab", description="Close current tab"),
        Binding(key="ctrl+pageup", action="previous_tab", description="Previous tab"),
        Binding(key="ctrl+pagedown", action="next_tab", description="Next tab"),
        Binding(key="alt+z", action="previous_tab", description="Previous tab"),
        Binding(key="alt+x", action="next_tab", description="Next tab"),
        #
        # Theme toggle
        Binding(key="ctrl+l", action="toggle_theme", description="Toggle theme"),
        #
        # Image rendering method toggle
        Binding(key="ctrl+i", action="toggle_image_method", description="Toggle image rendering"),
    ]
