import json
from pathlib import Path
from typing import TYPE_CHECKING

from textual.suggester import Suggester

from juicebox.settings import DATA_DIR
from juicebox.settings import BrowserSettings

if TYPE_CHECKING:
    from pathlib import Path


def get_history_file() -> Path:
    """Get the path to the history file.

    Returns:
        Path: The path to the history file.
    """
    # TODO(TheLovinator): Migrate to a database or more structured format later  # noqa: E501, TD003
    return DATA_DIR / "history.json"


def load_history() -> list[str]:
    """Load URL history from the history file.

    Returns:
        list[str]: A list of URLs from history, newest first.
            Returns empty list if file doesn't exist.
    """
    history_file: Path = get_history_file()
    if not history_file.exists():
        return []

    try:
        with history_file.open("r", encoding="utf-8") as f:
            data: list[str] = json.load(f)
            return data
    except json.JSONDecodeError, OSError:
        return []


def save_url_to_history(url: str, settings: BrowserSettings | None = None) -> None:
    """Save a URL to the history file.

    URLs are stored with newest first. Duplicates are removed (moved to top).
    Maximum URLs kept is determined by settings.history_limit.

    Args:
        url: The URL to save to history.
        settings: Browser settings to use. Creates default if not provided.

    """
    if settings is None:
        settings = BrowserSettings()

    history: list[str] = load_history()

    # Remove the URL if it already exists (we'll add it to the front)
    if url in history:
        history.remove(url)

    # Add URL to the front
    history.insert(0, url)

    # Keep only the most recent URLs based on settings
    history = history[: settings.history_limit]

    # Save to file
    history_file: Path = get_history_file()
    try:
        with history_file.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except OSError:
        # TODO(TheLovinator): Don't actually fail silently  # noqa: TD003
        pass  # Fail silently if we can't write history


class URLSuggester(Suggester):
    """Suggester that provides URL completions from browsing history."""

    def __init__(self) -> None:
        """Initialize the URLSuggester with cached history."""
        super().__init__(use_cache=False, case_sensitive=False)
        self._history: list[str] = []

    async def get_suggestion(self, value: str) -> str | None:
        """Get a URL suggestion based on the current input value.

        Args:
            value: The current input value.

        Returns:
            str | None: A suggested URL completion, or None if no match found.
        """
        # Don't suggest anything if value is empty or just whitespace
        if not value or not value.strip():
            return None

        # Refresh history on each call to get latest URLs
        self._history = load_history()

        # Find first matching URL (case-insensitive)
        value_lower: str = value.lower()
        for url in self._history:
            # Strip common prefixes for matching
            url_normalized: str = url.lower()
            url_normalized = url_normalized.removeprefix("https://").removeprefix(
                "http://",
            )
            url_normalized = url_normalized.removeprefix("www.")

            if url_normalized.startswith(value_lower):
                return url

        return None
