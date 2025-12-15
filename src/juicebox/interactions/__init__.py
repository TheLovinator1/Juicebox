"""Custom interaction handlers for different websites and APIs.

This module provides a decorator-based system for registering custom
interaction handlers for different domains. Each interaction handler
can implement custom logic for fetching and processing content from
a specific domain or API.

Examples:
    Create a new interaction handler in a file named after the domain
    (e.g., reddit.py) in the interactions directory:

    >>> from juicebox.interactions import interaction
    >>> from juicebox.app import PageResult
    >>>
    >>> @interaction("reddit.com")
    >>> def handle_reddit(url: str, settings) -> PageResult:
    ...     # Custom logic to fetch from Reddit JSON API
    ...     return PageResult(url=url, status=200, markdown="...")

"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from juicebox.app import BrowserSettings
    from juicebox.app import PageResult

T = TypeVar("T")

# Registry mapping domains to their interaction handlers
_INTERACTION_REGISTRY: dict[str, Callable[[str, BrowserSettings], PageResult]] = {}


def interaction(domain: str) -> Callable[[T], T]:
    """Decorator to register a custom interaction handler for a domain.

    Args:
        domain: The domain name to handle (e.g., "reddit.com", "github.com").
            Can also be a full domain with subdomains.

    Returns:
        A decorator function that registers the handler.

    Examples:
        >>> @interaction("reddit.com")
        >>> def handle_reddit(url: str, settings: BrowserSettings) -> PageResult:
        ...     # Implementation here
        ...     pass

    """

    def decorator(handler: T) -> T:
        """Register the handler in the interaction registry.

        Args:
            handler: The handler function to register.

        Returns:
            The unmodified handler function.

        """
        _INTERACTION_REGISTRY[domain] = handler  # type: ignore[assignment]
        return handler

    return decorator


def get_interaction(
    domain: str,
) -> Callable[[str, BrowserSettings], PageResult] | None:
    """Get the interaction handler for a domain.

    Args:
        domain: The domain to look up (e.g., "reddit.com").

    Returns:
        The handler function if found, otherwise None.

    """
    return _INTERACTION_REGISTRY.get(domain)


def get_all_interactions() -> dict[str, Callable[[str, BrowserSettings], PageResult]]:
    """Get all registered interaction handlers.

    Returns:
        A dictionary mapping domains to their handler functions.

    """
    return _INTERACTION_REGISTRY.copy()


__all__: list[str] = [
    "get_all_interactions",
    "get_interaction",
    "interaction",
]
