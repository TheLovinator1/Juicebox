"""Base class for site handlers in Juicebox."""

from __future__ import annotations

import re
from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from juicebox.app import JuiceboxApp
    from juicebox.models import PageResult


class SiteHandler(ABC):
    """Base class for all site-specific handlers.

    This class defines the interface and common properties for handling
    different websites in Juicebox. Each site should inherit from this
    class and implement the abstract methods.

    Attributes:
        name: Human-readable name of the site (e.g., "Reddit")
        description: Brief description of what content can be viewed
        tags: List of tags describing the site (e.g., ["social", "news"])
        requires_api_key: Whether the site requires API keys for access
        url_patterns: List of regex patterns that match URLs this handler supports
    """

    name: str = ""
    description: str = ""
    tags: list[str]
    requires_api_key: bool = False
    url_patterns: list[str | re.Pattern[str]]

    def __init__(self) -> None:
        """Initialize the site handler."""
        self.tags = []
        self.url_patterns = []

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """Check if this handler can process the given URL.

        Args:
            url: The URL to check.

        Returns:
            True if this handler can process the URL, False otherwise.
        """

    @abstractmethod
    async def handle(self, url: str, app: JuiceboxApp) -> PageResult:
        """Process the URL and return the rendered page content.

        Args:
            url: The URL to process.
            app: The Juicebox application instance.

        Returns:
            A PageResult containing the processed content.

        Raises:
            BrowserError: If processing fails.
        """

    def matches_url_pattern(self, url: str) -> bool:
        """Check if the URL matches any of the site's URL patterns.

        Args:
            url: The URL to check.

        Returns:
            True if the URL matches a pattern, False otherwise.
        """
        for url_pattern in self.url_patterns:
            compiled_pattern: re.Pattern[str] = (
                re.compile(url_pattern, re.IGNORECASE) if isinstance(url_pattern, str) else url_pattern
            )
            if compiled_pattern.search(url):
                return True
        return False
