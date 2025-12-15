from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from curl_cffi import requests
from markdownify import markdownify as html_to_md
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import (
    Footer,
    Header,
    Input,
    Markdown,
    Tab,
    Tabs,
)


@dataclass
class PageResult:
    """Represents the result of processing a web page.

    Attributes:
        url: The URL of the processed page.
        status: The HTTP status code returned by the page.
        markdown: The markdown representation of the page content.
        error: Optional error message if processing failed.

    """

    url: str
    """The URL of the processed page."""

    status: int
    """The HTTP status code returned by the page."""

    markdown: str
    """The markdown representation of the page content."""

    error: str | None = None
    """Optional error message if processing failed."""


def fetch_markdown(url: str) -> PageResult:
    """Fetch a URL and convert its HTML to Markdown.

    If the response contains non-HTML, we still show the text content.

    Args:
        url: The URL to fetch.

    Returns:
        A PageResult containing the URL, status code, markdown content, and any error.

    """
    # Basic scheme defaulting: if user typed a bare domain, assume https
    normalized: str = url.strip()
    if not normalized:
        return PageResult(url=url, status=0, markdown="", error="Empty URL")

    if "://" not in normalized:
        normalized = f"https://{normalized}"

    try:
        # Use curl_cffi for HTTP(S), with a reasonable UA
        resp: requests.Response = requests.get(
            normalized,
            timeout=20,
            impersonate="firefox",
        )
        content_type: str = resp.headers.get("content-type", "").lower()
        text: str = resp.text or ""
        if "html" in content_type:
            md: str = html_to_md(text, heading_style="ATX")
        else:
            # Fallback: just present the raw text
            md = "```\n" + text + "\n```"
        return PageResult(url=resp.url, status=resp.status_code, markdown=md)

    except Exception as e:  # noqa: BLE001
        return PageResult(url=normalized, status=0, markdown="", error=str(e))


class JuiceboxApp(App[None]):
    """Juicebox TUI web browser (minimal).

    Allows typing a domain/URL, fetches the page, converts to Markdown,
    and displays it in a scrollable pane.
    """

    current_page: PageResult | None = None
    markdown: Markdown
    current_tabs: int = 1

    BINDINGS = [  # noqa: RUF012
        Binding(
            key="q",
            action="quit",
            description="Quit the app",
        ),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
        ),
        #
        # Move around with WASD
        Binding(
            key="w",
            action="up",
            description="Scroll up",
            tooltip="Scroll up",
        ),
        Binding(
            key="s",
            action="down",
            description="Scroll down",
            tooltip="Scroll down",
        ),
        Binding(
            key="a",
            action="left",
            description="Go left",
            tooltip="Go left",
        ),
        Binding(
            key="d",
            action="right",
            description="Go right",
            tooltip="Go right",
        ),
        #
        # Refresh with r, ctrl+r or F5
        Binding(
            key="r",
            action="refresh",
            description="Refresh the page",
            show=False,
        ),
        Binding(
            key="f5",
            action="refresh",
            description="Refresh the page",
            show=False,
        ),
        Binding(
            key="ctrl+r",
            action="refresh",
            description="Refresh the page",
        ),
        #
        # URL entry
        Binding(
            key="ctrl+e",
            action="open_url",
            description="Enter a new URL",
        ),
        #
        # Search within page
        Binding(
            key="ctrl+f",
            action="search",
            description="Search in page",
        ),
        #
        # Search within all tabs
        Binding(
            key="ctrl+shift+f",
            action="search",
            description="Search in all tabs",
        ),
        #
        # Tab management
        Binding(
            key="ctrl+t",
            action="new_tab",
            description="Open new tab",
        ),
        Binding(
            key="ctrl+w",
            action="close_tab",
            description="Close current tab",
        ),
        # Dark mode toggle
        Binding(
            key="ctrl+l",
            action="toggle_dark",
            description="Toggle dark mode",
        ),
    ]

    def action_refresh(self) -> None:
        """Refresh the current page."""
        if self.current_page:
            self.sub_title = f"Refreshing {self.current_page.url}..."
            self.refresh(layout=True)
            page_result: PageResult = fetch_markdown(self.current_page.url)
            self.current_page = page_result
            self.markdown.update(page_result.markdown)
            self.sub_title = f"Status: {page_result.status}"

            self.notify(f"Refreshed {self.current_page.url}")
        else:
            self.sub_title = "No page to refresh."

    def action_search(self) -> None:
        """Search within the current page."""
        self.sub_title = "Search not implemented yet."

    def action_up(self) -> None:
        """Scroll up the content."""
        self.markdown.scroll_up()

    def action_down(self) -> None:
        """Scroll down the content."""
        self.markdown.scroll_down()

    def action_left(self) -> None:
        """Scroll left the content."""
        self.markdown.scroll_left()

    def action_right(self) -> None:
        """Scroll right the content."""
        self.markdown.scroll_right()

    def action_open_url(self) -> None:
        """Prompt for a new URL to fetch."""
        self.sub_title = "Enter URL..."

        # Get or create the input widget
        try:
            input_widget: Input = self.query_one("#url_input", Input)
        except Exception:  # noqa: BLE001
            # Input doesn't exist yet, add it
            self.query_one(Tabs).disabled = True
            input_widget = Input(
                placeholder="Enter URL and press Enter",
                id="url_input",
            )
            self.query_one(Markdown).mount(input_widget, before=self.query_one(Footer))

        input_widget.focus()
        self.notify("Prompting for new URL")

    def action_new_tab(self) -> None:
        """Open a new tab (not implemented)."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.add_tab(Tab(f"Tab {self.current_tabs}"))
        self.current_tabs += 1

        self.notify(f"Opened Tab {self.current_tabs}", timeout=1)

    def action_close_tab(self) -> None:
        """Close the current tab (not implemented)."""
        tabs: Tabs = self.query_one(Tabs)
        active_tab: Tab | None = tabs.active_tab
        if active_tab is not None:
            tabs.remove_tab(active_tab.id)
            if self.current_tabs > 1:
                self.current_tabs -= 1
            self.notify(f"Closed {active_tab.label}", timeout=1)

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        if self.theme == "textual-dark":
            theme: Literal["textual-dark", "textual-light"] = "textual-light"
        else:
            theme = "textual-dark"

        self.theme = theme

        self.notify(f"Toggled to {self.theme} theme", timeout=1)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL input submission.

        Args:
            event: The input submitted event.

        """
        url: str = event.value.strip()
        self.sub_title = f"Fetching {url}..."
        self.refresh(layout=True)

        page_result: PageResult = fetch_markdown(url)
        self.current_page = page_result

        if page_result.error:
            content: str = f"# Error fetching page\n\n{page_result.error}\n"
        else:
            content = page_result.markdown

        self.markdown.update(content)
        self.title = f"Juicebox - {page_result.url}"
        self.sub_title = f"Status: {page_result.status}"

    def compose(self) -> ComposeResult:
        """Apply the UI layout.

        Layout consists of a header, a markdown content area, and a footer.

        Yields:
            ComposeResult: The UI components.

        """
        # Header
        yield Header(show_clock=True, id="header", icon="🧃")
        yield Tabs(Tab(f"Tab {self.current_tabs}"), id="tabs")

        # The main browser area
        self.markdown = Markdown("", id="content")
        yield self.markdown

        # Footer
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Juicebox"
        self.sub_title = "about:juicebox"

        self.query_one(Tabs).focus()
