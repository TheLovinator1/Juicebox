import json
from pathlib import Path
from typing import Any

import pytest

from juicebox.interactions.reddit import RedditPathComponents
from juicebox.interactions.reddit import RedditResponse
from juicebox.interactions.reddit import create_markdown_for_post
from juicebox.interactions.reddit import get_reddit_path


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://old.reddit.com/",
            RedditPathComponents(subreddit=None, post_id=None, type="home"),
        ),
        (
            "https://www.reddit.com/",
            RedditPathComponents(subreddit=None, post_id=None, type="home"),
        ),
        (
            "https://reddit.com/",
            RedditPathComponents(subreddit=None, post_id=None, type="home"),
        ),
        (
            "https://old.reddit.com/?sort=top#frag",
            RedditPathComponents(subreddit=None, post_id=None, type="home"),
        ),
    ],
)
def test_home_paths(url: str, expected: RedditPathComponents) -> None:
    assert get_reddit_path(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://old.reddit.com/r/Games/",
            RedditPathComponents(subreddit="Games", post_id=None, type="subreddit"),
        ),
        (
            "https://old.reddit.com/r/Games",
            RedditPathComponents(subreddit="Games", post_id=None, type="subreddit"),
        ),
        (
            "https://www.reddit.com/r/python/",
            RedditPathComponents(subreddit="python", post_id=None, type="subreddit"),
        ),
    ],
)
def test_subreddit_listing_paths(url: str, expected: RedditPathComponents) -> None:
    assert get_reddit_path(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://old.reddit.com/r/Games/comments/1lqa2hj/has_xbox_considered/",
            RedditPathComponents(subreddit="Games", post_id="1lqa2hj", type="post"),
        ),
        (
            "https://www.reddit.com/r/python/comments/abc123",
            RedditPathComponents(subreddit="python", post_id="abc123", type="post"),
        ),
        (
            "https://old.reddit.com/comments/def456/title_doesnt_matter/",
            RedditPathComponents(subreddit=None, post_id="def456", type="post"),
        ),
    ],
)
def test_post_paths(url: str, expected: RedditPathComponents) -> None:
    assert get_reddit_path(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://old.reddit.com/r/Games/comments/",
            RedditPathComponents(subreddit="Games", post_id=None, type="subreddit"),
        ),
        (
            "https://old.reddit.com/comments/",
            RedditPathComponents(subreddit=None, post_id=None, type="unknown"),
        ),
    ],
)
def test_comments_without_id(url: str, expected: RedditPathComponents) -> None:
    assert get_reddit_path(url) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "https://old.reddit.com/u/killyoy",
            RedditPathComponents(subreddit=None, post_id=None, type="unknown"),
        ),
        (
            "https://old.reddit.com/user/killyoy",
            RedditPathComponents(subreddit=None, post_id=None, type="unknown"),
        ),
        (
            "https://old.reddit.com/r/",
            RedditPathComponents(subreddit=None, post_id=None, type="unknown"),
        ),
        (
            "https://old.reddit.com/settings",
            RedditPathComponents(subreddit=None, post_id=None, type="unknown"),
        ),
    ],
)
def test_unknown_or_incomplete_paths_fallback_home(
    url: str,
    expected: RedditPathComponents,
) -> None:
    assert get_reddit_path(url) == expected


@pytest.fixture
def subreddit_fixture() -> dict[str, Any]:
    """Load the subreddit fixture from JSON.

    Returns:
        A dictionary containing the subreddit listing JSON data.
    """
    fixture_path = Path(__file__).parent / "reddit_subreddit.json"
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def user_fixture() -> dict[str, Any]:
    """Load the user/comments fixture from JSON.

    Returns:
        A dictionary containing the user comments listing JSON data.
    """
    fixture_path = Path(__file__).parent / "reddit_user.json"
    with fixture_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def test_create_markdown_for_post_with_subreddit_fixture(
    subreddit_fixture: dict[str, Any],
) -> None:
    """Test post markdown creation with a real subreddit fixture."""
    listing = RedditResponse.model_validate(subreddit_fixture)
    post = listing.data.children[0]

    md = create_markdown_for_post(post)

    # Verify the markdown contains expected components
    assert "## [The 2025 Game Awards Megathread]" in md
    assert "rGamesMods" in md
    assert "Games" in md
    assert "👍" in md  # Score emoji
    assert "reddit.com" in md
