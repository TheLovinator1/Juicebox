from typing import TYPE_CHECKING

from textual.widget import Widget
from textual.widgets import Label
from textual.widgets import Pretty
from webscrapers.reddit import RedditCommentData
from webscrapers.reddit import RedditPostData
from webscrapers.reddit import scrape_post

from juicebox.models import PageResult

if TYPE_CHECKING:
    from rnet import Response
    from textual.app import ComposeResult


class RedditComment(Widget):
    def __init__(self, data: RedditCommentData) -> None:
        self.data: RedditCommentData = data
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(f"{self.data.author} @ {self.data.date_posted}")
        yield Label(f"{self.data.content_text}")


def _render_reddit_content(data: RedditPostData) -> PageResult:
    # A list of widgets, each widget is a Reddit comment.
    widgets: list[Widget] = [RedditComment(comment) for comment in data.comments]
    return PageResult(
        url=data.permalink or "",
        widgets=widgets,
        status=data.response.status,
    )


async def handle_reddit(url: str) -> PageResult:
    """Handle Reddit URLs by scraping the site.

    Args:
        url: The Reddit URL to fetch.

    Returns:
        A PageResult containing the processed Reddit content.

    """
    reddit_post_data: RedditPostData = await scrape_post(post_url=url)
    response: Response = reddit_post_data.response

    if not response.ok:
        return PageResult(
            url=reddit_post_data.permalink or "",
            status=response.status,
            widgets=[Label(f"Error {response.status}"), Pretty(response.json)],
            error=f"Failed to access {url=}",
        )

    return _render_reddit_content(data=reddit_post_data)


__all__: list[str] = [
    "handle_reddit",
]
