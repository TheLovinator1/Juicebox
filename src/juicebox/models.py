from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.widget import Widget


@dataclass
class PageResult:
    """Represents the result of processing a web page.

    Attributes:
        url: The URL of the processed page.
        status: The HTTP status code returned by the page.
    """

    url: str
    """The URL of the processed page."""

    widgets: list[Widget]
    """List of widgets associated with the page."""

    title: str
    """The title of the page."""

    summary: str
    """A short summary or description of the page."""
