from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast
from urllib.parse import urlparse

from curl_cffi import requests
from markdownify import markdownify as html_to_md
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from textual.app import App
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.theme import Theme
from textual.widget import Widget
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Input
from textual.widgets import Markdown
from textual.widgets import Tab
from textual.widgets import Tabs

from juicebox.action.search import do_action_search
from juicebox.history import URLSuggester
from juicebox.history import save_url_to_history
from juicebox.hotkeys import get_hotkeys
from juicebox.interactions import get_interaction
from juicebox.interactions.loader import load_interactions
from juicebox.settings import BrowserSettings

if TYPE_CHECKING:
    from collections.abc import Callable

    from textual.theme import Theme


class PageResult(BaseModel):
    """Represents the result of processing a web page.

    Attributes:
        url: The URL of the processed page.
        status: The HTTP status code returned by the page.
        markdown: The markdown representation of the page content.
        error: Optional error message if processing failed.

    """

    # Allow arbitrary widget types in `widgets` without requiring pydantic schemas
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(
        ...,
        description="The URL of the processed page",
        min_length=1,
    )

    status: int = Field(
        ...,
        description="The HTTP status code returned by the page",
        ge=0,
        le=999,
    )

    markdown: str = Field(
        default="",
        description="The markdown representation of the page content",
    )

    widgets: list[Widget] = Field(
        default_factory=list[Widget],
        description="List of widgets associated with the page",
    )

    error: str | None = Field(
        default=None,
        description="Optional error message if processing failed",
    )

    @field_validator("url")
    @classmethod
    def validate_url_not_empty(cls, v: str) -> str:
        """Ensure URL is not empty or whitespace only.

        Args:
            v: The URL string to validate.

        Returns:
            The validated URL string.

        Raises:
            ValueError: If URL is empty or whitespace only.

        """
        if not v or not v.strip():
            msg = "URL cannot be empty"
            raise ValueError(msg)
        return v.strip()


def fetch_markdown(url: str, settings: BrowserSettings | None = None) -> PageResult:
    """Fetch a URL and convert its HTML to Markdown.

    First checks if there's a custom interaction handler for the domain.
    If not, fetches HTML and converts to Markdown.

    Args:
        url: The URL to fetch.
        settings: Browser settings to use. Creates default if not provided.

    Returns:
        A PageResult containing the URL, status code, markdown content, and any error.

    """
    if settings is None:
        settings = BrowserSettings()

    # Basic scheme defaulting: if user typed a bare domain, assume https
    normalized: str = url.strip()
    if not normalized:
        return PageResult(url=url, status=0, markdown="", error="Empty URL")

    if "://" not in normalized:
        normalized = f"{settings.default_scheme}://{normalized}"

    # Check for custom interaction handlers
    parsed_url = urlparse(normalized)
    domain = parsed_url.netloc.lower()

    # Try to find a handler for this domain
    # First try exact match
    handler: Callable[[str, BrowserSettings], PageResult] | None = get_interaction(
        domain,
    )
    if handler is not None:
        return handler(normalized, settings)

    # If not found, try removing common prefixes (www, old, new, m, mobile, compact)
    domain_parts: list[str] = domain.split(".")
    if len(domain_parts) > 2:  # noqa: PLR2004
        # Try removing the first subdomain
        domain_without_prefix = ".".join(domain_parts[1:])
        handler = get_interaction(domain_without_prefix)
        if handler is not None:
            return handler(normalized, settings)

    try:
        # Use curl_cffi for HTTP(S), with a reasonable UA
        resp: requests.Response = requests.get(
            normalized,
            timeout=settings.request_timeout,
            impersonate=settings.user_agent,
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
    settings: BrowserSettings
    tab_content: dict[str, PageResult | None]  # Maps tab ID to PageResult

    BINDINGS = get_hotkeys()

    def _get_active_tab_id(self) -> str | None:
        """Get the ID of the currently active tab.

        Returns:
            The active tab ID, or None if no tab is active.
        """
        tabs: Tabs = self.query_one(Tabs)
        active_tab: Tab | None = tabs.active_tab
        return active_tab.id if active_tab else None

    def _update_markdown_from_tab(self) -> None:
        """Update the content display to show the current tab's content."""
        tab_id: str | None = self._get_active_tab_id()
        if not tab_id:
            return

        page_result: PageResult | None = self.tab_content.get(tab_id)
        if page_result:
            self.current_page = page_result
            if page_result.error:
                content: str = f"# Error fetching page\n\n{page_result.error}\n"
                self.markdown.update(content)
                # Clear any widget content
                widgets_container: VerticalScroll = self.query_one(
                    "#content_widgets",
                    VerticalScroll,
                )
                widgets_container.remove_children()
            # If widgets are present, render them; otherwise fallback to markdown
            elif page_result.widgets:
                widgets_container = self.query_one(
                    "#content_widgets",
                    VerticalScroll,
                )
                widgets_container.remove_children()
                for w in page_result.widgets:
                    widgets_container.mount(w)
                self.markdown.update("")
            else:
                self.markdown.update(page_result.markdown)
            self.title = f"Juicebox - {page_result.url}"
            self.sub_title = f"Status: {page_result.status}"
        else:
            self.current_page = None
            self.markdown.update("")
            self.title = "Juicebox"
            self.sub_title = "about:juicebox"

    def action_refresh(self) -> None:
        """Refresh the current page."""
        if self.current_page:
            self.sub_title = f"Refreshing {self.current_page.url}..."
            self.refresh(layout=True)
            page_result: PageResult = fetch_markdown(
                self.current_page.url,
                self.settings,
            )

            # Update the tab content
            tab_id: str | None = self._get_active_tab_id()
            if tab_id:
                self.tab_content[tab_id] = page_result

            self.current_page = page_result
            if page_result.widgets:
                widgets_container: VerticalScroll = self.query_one(
                    "#content_widgets",
                    VerticalScroll,
                )
                widgets_container.remove_children()
                for w in page_result.widgets:
                    widgets_container.mount(w)
                self.markdown.update("")
            else:
                self.markdown.update(page_result.markdown)
            self.sub_title = f"Status: {page_result.status}"

            self.notify(f"Refreshed {self.current_page.url}")
        else:
            self.sub_title = "No page to refresh."

    def action_search(self) -> None:
        """Search within the current page."""
        do_action_search(self)

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
                suggester=URLSuggester(),
            )
            self.query_one(Markdown).mount(input_widget, before=self.query_one(Footer))

        # Clear the input value and any suggestion when opening URL input
        input_widget.value = ""
        input_widget.focus()

    def action_new_tab(self) -> None:
        """Open a new tab."""
        tabs: Tabs = self.query_one(Tabs)
        self.current_tabs += 1
        new_tab: Tab = Tab(f"Tab {self.current_tabs}")
        tabs.add_tab(new_tab)

        # Initialize empty content for the new tab and immediately focus it
        new_tab_id: str | None = new_tab.id
        if new_tab_id:
            self.tab_content[new_tab_id] = None

            max_activation_attempts: int = 3

            def activate_and_prompt(attempt: int = 0) -> None:
                try:
                    tabs.active = new_tab_id
                except ValueError:
                    # Tab may not be mounted yet; retry a few times.
                    if attempt < max_activation_attempts:
                        self.call_after_refresh(
                            lambda: activate_and_prompt(attempt + 1),
                        )
                    return

                self._update_markdown_from_tab()
                self.action_open_url()

            self.call_after_refresh(activate_and_prompt)

    def action_close_tab(self) -> None:
        """Close the current tab."""
        tabs: Tabs = self.query_one(Tabs)
        active_tab: Tab | None = tabs.active_tab
        if active_tab is not None and active_tab.id:
            tab_id: str = active_tab.id
            # Remove tab content from storage
            if tab_id in self.tab_content:
                del self.tab_content[tab_id]

            tabs.remove_tab(tab_id)
            if self.current_tabs > 1:
                self.current_tabs -= 1
            self.notify(f"Closed {active_tab.label}", timeout=1)

            # Update display to show the newly active tab
            self._update_markdown_from_tab()

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_next_tab()
        self._update_markdown_from_tab()

    def action_previous_tab(self) -> None:
        """Switch to the previous tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()
        self._update_markdown_from_tab()

    def action_toggle_theme(self) -> None:
        """Toggle between all the available themes."""
        # All available themes (all built-in themes plus any that have been registered).
        # A dictionary mapping theme names to Theme instances.
        available_themes: dict[str, Theme] = self.available_themes
        current_theme: Theme = self.current_theme

        # Find the next theme in the list
        theme_names: list[str] = list(available_themes.keys())
        try:
            current_index: int = theme_names.index(current_theme.name)
            next_index: int = (current_index + 1) % len(theme_names)
        except ValueError:
            next_index = 0  # Fallback to first theme if current not found
            self.notify(
                message="Current theme not found in available themes, switching to first theme.",  # noqa: E501
                timeout=2,
                severity="error",
            )

        next_theme_name: str = theme_names[next_index]
        self.theme = next_theme_name
        self.notify(
            f"Switched to theme: {next_theme_name} ({next_index + 1}/{len(theme_names)})",  # noqa: E501
            timeout=1,
        )

    def action_toggle_image_method(self) -> None:
        """Toggle between image rendering methods."""
        methods: list[str] = ["auto", "tgp", "sixel", "unicode", "halfcell"]
        current: str = self.settings.image_method
        try:
            current_index: int = methods.index(current)
            next_index: int = (current_index + 1) % len(methods)
        except ValueError:
            next_index = 0  # Fallback to auto if current not found

        next_method = cast(
            "Literal['auto', 'tgp', 'sixel', 'unicode', 'halfcell']",
            methods[next_index],
        )
        self.settings.image_method = next_method

        # Update environment variable so it's picked up on next fetch
        os.environ["JUICEBOX_IMAGE_METHOD"] = next_method

        self.notify(
            f"Image method: {next_method} ({next_index + 1}/{len(methods)})",
            timeout=2,
        )

        # Refresh to apply new image method
        if self.current_page:
            self.action_refresh()

    def on_tabs_tab_activated(self) -> None:
        """Handle tab activation (switching tabs)."""
        self._update_markdown_from_tab()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL input submission.

        Args:
            event: The input submitted event.

        """
        url: str = event.value.strip()
        self.sub_title = f"Fetching {url}..."
        self.refresh(layout=True)

        page_result: PageResult = fetch_markdown(url, self.settings)

        # Store the result for the current tab
        tab_id: str | None = self._get_active_tab_id()
        if tab_id:
            self.tab_content[tab_id] = page_result

        self.current_page = page_result

        if page_result.error:
            content: str = f"# Error fetching page\n\n{page_result.error}\n"
            self.markdown.update(content)
            # Clear any widget content on error
            self.query_one("#content_widgets", VerticalScroll).remove_children()
        else:
            # Save to history only if successful
            save_url_to_history(page_result.url, self.settings)
            if page_result.widgets:
                widgets_container: VerticalScroll = self.query_one(
                    "#content_widgets",
                    VerticalScroll,
                )
                widgets_container.remove_children()
                for w in page_result.widgets:
                    widgets_container.mount(w)
                self.markdown.update("")
            else:
                self.markdown.update(page_result.markdown)
        self.title = f"Juicebox - {page_result.url}"
        self.sub_title = f"Status: {page_result.status}"

        # Hide the input widget and restore focus to tabs
        try:
            input_widget: Input = self.query_one("#url_input", Input)
            input_widget.remove()
            self.query_one(Tabs).disabled = False
            self.query_one(Tabs).focus()
        except Exception:  # noqa: BLE001, S110
            pass

    def compose(self) -> ComposeResult:
        """Apply the UI layout.

        Layout consists of a header, a markdown content area, and a footer.

        Yields:
            ComposeResult: The UI components.

        """
        # Header
        yield Header(show_clock=True, id="header", icon="🧃")
        yield Tabs(Tab(f"Tab {self.current_tabs}"), id="tabs")

        # The main browser area: markdown plus a scroll container for widgets
        self.markdown = Markdown("", id="content")
        yield self.markdown
        yield VerticalScroll(id="content_widgets")

        # Footer
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        # Load custom interaction handlers
        load_interactions()

        # Load settings
        self.settings = BrowserSettings()

        # Apply theme from settings
        self.theme = self.settings.theme

        self.title = "Juicebox"
        self.sub_title = "about:juicebox"

        # Initialize tab content dictionary
        self.tab_content = {}

        # Initialize the first tab
        tab_id: str | None = self._get_active_tab_id()
        if tab_id:
            self.tab_content[tab_id] = None

        self.query_one(Tabs).focus()


app = JuiceboxApp()

if __name__ == "__main__":
    app.run()
