from __future__ import annotations

import json
from typing import TYPE_CHECKING, Literal

from curl_cffi import requests
from curl_cffi.requests import BrowserTypeLiteral  # noqa: TC002
from markdownify import markdownify as html_to_md
from platformdirs import user_config_path, user_data_path
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.suggester import Suggester
from textual.theme import Theme
from textual.widgets import (
    Footer,
    Header,
    Input,
    Markdown,
    Tab,
    Tabs,
)

if TYPE_CHECKING:
    from pathlib import Path

    from textual.theme import Theme

# History and data that needs to persist between runs
DATA_DIR: Path = user_data_path(
    appname="Juicebox",
    appauthor="TheLovinator",
    roaming=True,
    ensure_exists=True,
)

# Configuration directory - settings etc.
CONFIG_DIR: Path = user_config_path(
    appname="Juicebox",
    appauthor="TheLovinator",
    roaming=True,
    ensure_exists=True,
)


class BrowserSettings(BaseSettings):
    """Browser configuration settings.

    Uses pydantic-settings to load from environment variables and config files.
    Settings can be overridden via JUICEBOX_* environment variables.
    """

    model_config = SettingsConfigDict(
        env_prefix="JUICEBOX_",
        env_file=CONFIG_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    theme: Literal["textual-dark", "textual-light"] = Field(
        default="textual-dark",
        description="Default theme for the browser",
    )

    history_limit: int = Field(
        default=1000,
        gt=0,
        le=10000,
        description="Maximum number of URLs to keep in history",
    )

    request_timeout: int = Field(
        default=20,
        gt=0,
        le=120,
        description="HTTP request timeout in seconds",
    )

    user_agent: BrowserTypeLiteral = Field(
        default="firefox",
        description="Browser to impersonate for curl_cffi",
    )

    default_scheme: str = Field(
        default="https",
        description="Default URL scheme if none provided",
    )


def get_history_file() -> Path:
    """Get the path to the history file.

    Returns:
        Path: The path to the history file.
    """
    # TODO(TheLovinator): Migrate to a database or more structured format later  # noqa: TD003
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
                "http://"
            )
            url_normalized = url_normalized.removeprefix("www.")

            if url_normalized.startswith(value_lower):
                return url

        return None


class PageResult(BaseModel):
    """Represents the result of processing a web page.

    Attributes:
        url: The URL of the processed page.
        status: The HTTP status code returned by the page.
        markdown: The markdown representation of the page content.
        error: Optional error message if processing failed.

    """

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

    If the response contains non-HTML, we still show the text content.

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

    BINDINGS = [  # noqa: RUF012
        Binding(
            key="q",
            action="quit",
            description="Quit the app",
            priority=True,
        ),
        Binding(
            key="question_mark",
            action="help",
            description="Show help screen",
            key_display="?",
            priority=True,
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
            priority=True,
        ),
        #
        # URL entry
        Binding(
            key="ctrl+e",
            action="open_url",
            description="Enter a new URL",
            priority=True,
        ),
        #
        # Search within page
        Binding(
            key="ctrl+f",
            action="search",
            description="Search in page",
            priority=True,
        ),
        #
        # Search within all tabs
        Binding(
            key="ctrl+shift+f",
            action="search",
            description="Search in all tabs",
            priority=True,
        ),
        #
        # Tab management
        Binding(
            key="ctrl+t",
            action="new_tab",
            description="Open new tab",
            priority=True,
        ),
        Binding(
            key="ctrl+w",
            action="close_tab",
            description="Close current tab",
            priority=True,
        ),
        Binding(
            key="ctrl+pageup",
            action="previous_tab",
            description="Previous tab",
            priority=True,
        ),
        Binding(
            key="ctrl+pagedown",
            action="next_tab",
            description="Next tab",
            priority=True,
        ),
        Binding(
            key="alt+z",
            action="previous_tab",
            description="Previous tab",
            priority=True,
        ),
        Binding(
            key="alt+x",
            action="next_tab",
            description="Next tab",
            priority=True,
        ),
        #
        # Theme toggle
        Binding(
            key="ctrl+l",
            action="toggle_theme",
            description="Toggle theme",
            priority=True,
        ),
    ]

    def _get_active_tab_id(self) -> str | None:
        """Get the ID of the currently active tab.

        Returns:
            The active tab ID, or None if no tab is active.
        """
        tabs: Tabs = self.query_one(Tabs)
        active_tab: Tab | None = tabs.active_tab
        return active_tab.id if active_tab else None

    def _update_markdown_from_tab(self) -> None:
        """Update the markdown display to show the current tab's content."""
        tab_id: str | None = self._get_active_tab_id()
        if not tab_id:
            return

        page_result: PageResult | None = self.tab_content.get(tab_id)
        if page_result:
            self.current_page = page_result
            if page_result.error:
                content: str = f"# Error fetching page\n\n{page_result.error}\n"
            else:
                content = page_result.markdown
            self.markdown.update(content)
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

        # Initialize empty content for the new tab
        if new_tab.id:
            self.tab_content[new_tab.id] = None
            tabs.show(new_tab.id)

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
        self.notify("Switched to next tab", timeout=1)

    def action_previous_tab(self) -> None:
        """Switch to the previous tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()
        self._update_markdown_from_tab()
        self.notify("Switched to previous tab", timeout=1)

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
        else:
            content = page_result.markdown
            # Save to history only if successful
            save_url_to_history(page_result.url, self.settings)

        self.markdown.update(content)
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

        # The main browser area
        self.markdown = Markdown("", id="content")
        yield self.markdown

        # Footer
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
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
