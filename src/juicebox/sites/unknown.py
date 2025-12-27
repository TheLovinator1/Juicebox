from typing import TYPE_CHECKING

from textual.widgets import Label
from textual.widgets import Pretty

from juicebox.http import request_get
from juicebox.models import PageResult

if TYPE_CHECKING:
    from curl_cffi import requests


def _render_content(response: requests.Response) -> PageResult:
    """Convert HTML to Markdown and return.

    Args:
        response (requests.Response): Contains information from the URL we accessed.

    Returns:
        PageResult: Represents the result of processing a web page.
    """
    # TODO(TheLovinator): We should make our own version of Reader-mode before converting to markdown.  # noqa: E501, TD003

    return PageResult(
        markdown=response.markdown(),
        url=response.url,
        status=response.status_code,
    )


async def handle_unknown(url: str) -> PageResult:
    """This is for sites that we don't have support for.

    Args:
        url: The URL to fetch.

    Returns:
        A PageResult containing the website content.

    """
    response: requests.Response = await request_get(url=url)

    if not response.ok:
        return PageResult(
            url=url,
            status=response.status_code,
            widgets=[
                Label(f"Error {response.status_code} - {response.reason}"),
                Pretty(response.json),  # pyright: ignore[reportUnknownMemberType]
            ],
            error=f"Failed to access {url=}",
        )

    return _render_content(response=response)
