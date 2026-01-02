"""Site handlers for Juicebox."""

from __future__ import annotations

from juicebox.sites.base import SiteHandler
from juicebox.sites.reddit import RedditHandler
from juicebox.sites.unknown import UnknownHandler

__all__: list[str] = ["RedditHandler", "SiteHandler", "UnknownHandler", "get_site_handler"]

# Registry of all available site handlers
_HANDLERS: list[SiteHandler] = [
    RedditHandler(),
    UnknownHandler(),  # Must be last as fallback
]


async def get_site_handler(url: str) -> SiteHandler:
    """Get the appropriate site handler for the given URL.

    Handlers are checked in order, so the UnknownHandler should always be last
    as a fallback.

    Args:
        url: The URL to find a handler for.

    Returns:
        The SiteHandler that can handle the URL.
    """
    for handler in _HANDLERS:
        if await handler.can_handle(url):
            return handler

    # This should never happen since UnknownHandler handles all URLs
    return _HANDLERS[-1]
