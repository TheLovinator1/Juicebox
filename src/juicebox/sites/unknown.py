"""Handler for unknown/unsupported sites."""

from __future__ import annotations

from typing import TYPE_CHECKING

from markdownify import markdownify
from selectolax.parser import HTMLParser
from selectolax.parser import Node
from textual.widgets import Markdown

from juicebox.exceptions import BrowserError
from juicebox.http import request_aget
from juicebox.models import PageResult
from juicebox.sites.base import SiteHandler

if TYPE_CHECKING:
    from curl_cffi import requests

    from juicebox.app import JuiceboxApp


async def handle_unknown(url: str, app: JuiceboxApp) -> PageResult:
    """This is for sites that we don't have support for.

    Args:
        url: The URL to fetch.
        app: The Juicebox application instance.

    Raises:
        BrowserError: If response was not ok.

    Returns:
        A PageResult containing the website content.

    """
    response: requests.Response = await request_aget(url=url, app=app)

    if not response.ok:
        msg: str = f"Failed to access {url=}\n{response}"
        raise BrowserError(msg)

    # Use selectolax to extract <title> and meta description
    html: str = response.text
    tree = HTMLParser(html)

    # Extract <title>
    title_node: Node | None = tree.css_first("title")
    title: str = title_node.text(strip=True) if title_node else response.url

    # Extract meta description or og:description
    summary: str = extract_summary(tree)

    md: str = markdownify(html)
    return PageResult(widgets=[Markdown(markdown=md)], url=response.url, title=title, summary=summary)


def extract_summary(tree: HTMLParser) -> str:
    """Extracts and combines summary text from Open Graph and meta description content.

    Args:
        tree: The parsed HTML tree.

    Returns:
        str: A summary string composed from the meta description and/or Open Graph
            description. If both are present and different, they are concatenated with a
            newline. If only one is present, it is returned. If neither is present,
            returns an empty string.
    """
    summary: str = ""
    og_content: str = ""
    meta_content: str = ""

    og_desc: Node | None = tree.css_first('meta[property="og:description"]')
    if og_desc and og_desc.attributes.get("content"):
        content: str | None = og_desc.attributes["content"]
        if content:
            og_content = content.strip()

    meta_desc: Node | None = tree.css_first('meta[name="description"]')
    if meta_desc and meta_desc.attributes.get("content"):
        content: str | None = meta_desc.attributes["content"]
        if content:
            meta_content = content.strip()

    if meta_content and og_content:
        summary = f"{meta_content}\n{og_content}" if meta_content != og_content else meta_content

    elif meta_content:
        summary = meta_content

    elif og_content:
        summary = og_content

    return summary


class UnknownHandler(SiteHandler):
    """Fallback handler for unknown/unsupported websites."""

    def __init__(self) -> None:
        """Initialize the unknown site handler."""
        super().__init__()
        self.name = "Unknown/Unsupported Site"
        self.description = "Generic fallback handler for any website"
        self.tags = ["generic", "fallback"]
        self.requires_api_key = False
        self.url_patterns = [r".*"]  # Matches any URL

    async def can_handle(self, url: str) -> bool:
        """This handler can handle any URL.

        Args:
            url: The URL to check.

        Returns:
            Always returns True as this is the fallback handler.
        """
        return True

    async def handle(self, url: str, app: JuiceboxApp) -> PageResult:
        """Handle any unknown website by extracting and rendering its content.

        Args:
            url: The website URL to process.
            app: The Juicebox application instance.

        Returns:
            A PageResult with the converted HTML content.
        """
        return await handle_unknown(url=url, app=app)
