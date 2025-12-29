from typing import TYPE_CHECKING

from markdownify import markdownify
from textual.widgets import Markdown

from juicebox.exceptions import BrowserError
from juicebox.http import request_aget
from juicebox.models import PageResult

if TYPE_CHECKING:
    from curl_cffi import requests


async def handle_unknown(url: str) -> PageResult:
    """This is for sites that we don't have support for.

    Args:
        url: The URL to fetch.

    Raises:
        BrowserError: If response was not ok.

    Returns:
        A PageResult containing the website content.

    """
    response: requests.Response = await request_aget(url=url)

    if not response.ok:
        msg: str = f"Failed to access {url=}\n{response}"
        raise BrowserError(msg)

    # TODO(TheLovinator): We should make our own version of Reader-mode before converting to markdown.  # noqa: E501, TD003
    md: str = markdownify(response.text)

    return PageResult(
        widgets=[Markdown(markdown=md)],
        url=response.url,
    )
