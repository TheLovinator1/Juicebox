from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from juicebox.exceptions import BrowserError
from juicebox.models import PageResult
from juicebox.sites.reddit import RedditCommentData
from juicebox.sites.reddit import RedditHandler
from juicebox.sites.reddit import RedditPostData
from juicebox.sites.reddit import RedditScraperError


@pytest.fixture
def mock_app() -> MagicMock:
    """Create a mock JuiceboxApp instance.

    Returns:
        A MagicMock simulating JuiceboxApp.
    """
    return MagicMock()


@pytest.fixture
def sample_reddit_post_data() -> RedditPostData:
    """Create sample RedditPostData for testing.

    Returns:
        A RedditPostData instance with sample data.
    """
    comment = RedditCommentData(
        comment_id="abc123",
        author="test_user",
        content_html="<p>Test comment</p>",
        content_text="Test comment",
        score=10,
    )
    return RedditPostData(
        post_id="xyz789",
        title="Test Post",
        author="post_author",
        subreddit="test",
        permalink="/r/test/comments/xyz789/test_post/",
        comments=(comment,),
        is_ok=True,
    )


@pytest.fixture
def reddit_handler() -> RedditHandler:
    """Create a RedditHandler instance.

    Returns:
        An instance of RedditHandler.
    """
    return RedditHandler()


@pytest.mark.asyncio
async def test_handle_success(
    reddit_handler: RedditHandler,
    mock_app: MagicMock,
    sample_reddit_post_data: RedditPostData,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test successful Reddit URL handling."""
    mock_handle_reddit = AsyncMock(return_value=MagicMock(spec=PageResult))
    monkeypatch.setattr("juicebox.sites.reddit.handle_reddit", mock_handle_reddit)

    url = "https://reddit.com/r/test/comments/xyz789/test_post/"
    result: PageResult = await reddit_handler.handle(url=url, app=mock_app)

    mock_handle_reddit.assert_called_once_with(url=url, app=mock_app)
    assert isinstance(result, PageResult)


@pytest.mark.asyncio
async def test_handle_scraper_error(
    reddit_handler: RedditHandler,
    mock_app: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling when scraping fails."""
    mock_handle_reddit = AsyncMock(side_effect=RedditScraperError("Scraping failed"))
    monkeypatch.setattr("juicebox.sites.reddit.handle_reddit", mock_handle_reddit)

    url = "https://reddit.com/r/test/comments/invalid/"

    with pytest.raises(RedditScraperError):
        await reddit_handler.handle(url=url, app=mock_app)


@pytest.mark.asyncio
async def test_handle_not_ok_response(
    reddit_handler: RedditHandler,
    mock_app: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test handling when Reddit response is not OK."""
    failed_post_data = RedditPostData(
        post_id="xyz789",
        is_ok=False,
    )

    mock_scrape_post = AsyncMock(return_value=failed_post_data)
    monkeypatch.setattr("juicebox.sites.reddit.scrape_post", mock_scrape_post)

    url = "https://reddit.com/r/test/comments/xyz789/"

    with pytest.raises(BrowserError):
        await reddit_handler.handle(url=url, app=mock_app)


@pytest.mark.asyncio
async def test_handle_delegates_to_handle_reddit(
    reddit_handler: RedditHandler,
    mock_app: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that handle() correctly delegates to handle_reddit()."""
    expected_result = MagicMock(spec=PageResult)
    mock_handle_reddit = AsyncMock(return_value=expected_result)
    monkeypatch.setattr("juicebox.sites.reddit.handle_reddit", mock_handle_reddit)

    url = "https://old.reddit.com/r/python/comments/123/"
    result: PageResult = await reddit_handler.handle(url=url, app=mock_app)

    assert result == expected_result
    mock_handle_reddit.assert_called_once_with(url=url, app=mock_app)
