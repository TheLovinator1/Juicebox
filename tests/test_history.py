"""Tests for history management."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

import pytest

from juicebox.history import load_history
from juicebox.history import save_url_to_history
from juicebox.settings import BrowserSettings

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_history_dir() -> Generator[Path]:
    """Create a temporary directory for history testing.

    Yields:
        Path to the temporary directory.
    """
    with TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def test_save_url_with_json_suffix(
    temp_history_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that URLs are saved as-is.

    Reddit handler provides clean URLs without .json suffix.
    """
    # Override DATA_DIR to use temporary directory
    monkeypatch.setattr("juicebox.history.DATA_DIR", temp_history_dir)

    settings = BrowserSettings()

    # Save a URL without .json suffix (Reddit handler provides clean URLs)
    save_url_to_history("https://old.reddit.com/r/games", settings)

    # Load history and verify URL is saved correctly
    history = load_history()
    assert len(history) == 1
    assert history[0] == "https://old.reddit.com/r/games"


def test_save_url_without_json_suffix(
    temp_history_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that URLs without .json suffix are saved as-is."""
    monkeypatch.setattr("juicebox.history.DATA_DIR", temp_history_dir)

    settings = BrowserSettings()

    # Save a regular URL without .json
    save_url_to_history("https://www.python.org/", settings)

    # Load history and verify URL is unchanged
    history = load_history()
    assert len(history) == 1
    assert history[0] == "https://www.python.org/"


def test_save_multiple_urls(
    temp_history_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test saving multiple URLs."""
    monkeypatch.setattr("juicebox.history.DATA_DIR", temp_history_dir)

    settings = BrowserSettings()

    urls = [
        "https://old.reddit.com/r/games",
        "https://old.reddit.com/",
        "https://www.python.org/",
        "https://old.reddit.com/r/python",
    ]

    for url in urls:
        save_url_to_history(url, settings)

    # Load history and verify all URLs are saved correctly
    history = load_history()
    assert len(history) == 4
    assert history[0] == "https://old.reddit.com/r/python"  # Most recent
    assert history[1] == "https://www.python.org/"
    assert history[2] == "https://old.reddit.com/"
    assert history[3] == "https://old.reddit.com/r/games"


def test_save_duplicate_url(
    temp_history_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that saving a duplicate URL moves it to the top."""
    monkeypatch.setattr("juicebox.history.DATA_DIR", temp_history_dir)

    settings = BrowserSettings()

    # Save some URLs
    save_url_to_history("https://old.reddit.com/r/games", settings)
    save_url_to_history("https://www.python.org/", settings)
    save_url_to_history("https://old.reddit.com/r/python", settings)

    # Save the first URL again (should move to top, not duplicate)
    save_url_to_history("https://old.reddit.com/r/games", settings)

    history = load_history()
    assert len(history) == 3  # No duplicates
    assert history[0] == "https://old.reddit.com/r/games"  # Moved to top
    assert history[1] == "https://old.reddit.com/r/python"
    assert history[2] == "https://www.python.org/"
