from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from juicebox.app import JuiceboxApp


def do_action_search(self: JuiceboxApp) -> None:
    """Search within the current page."""
    self.sub_title = "Search not implemented yet."
