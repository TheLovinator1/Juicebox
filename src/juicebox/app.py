from __future__ import annotations

import os
from typing import TYPE_CHECKING

import tldextract
from sqlalchemy.engine.base import Engine
from sqlmodel import SQLModel
from sqlmodel import create_engine
from textual.app import App
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.containers import Vertical
from textual.theme import Theme
from textual.widgets import Button
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Input
from textual.widgets import Static
from textual.widgets import TabbedContent
from textual.widgets import TabPane
from textual.widgets import Tabs

from juicebox.exceptions import BrowserError
from juicebox.history import URLData
from juicebox.history import save_url_to_history
from juicebox.hotkeys import get_hotkeys
from juicebox.models import PageResult
from juicebox.settings import BrowserSettings
from juicebox.sites.reddit import handle_reddit
from juicebox.sites.unknown import handle_unknown

if TYPE_CHECKING:
    from sqlalchemy import Engine
    from textual.theme import Theme


async def fetch_site_contents(app: JuiceboxApp, url: str) -> PageResult:
    """These are the sites we have support for.

    Args:
        app (JuiceboxApp): The JuiceBox Textual Application
        url (str): The URL we want to browse to.

    Returns:
        Represents the result of processing a web page.
    """
    tld: tldextract.ExtractResult = tldextract.extract(url=url)
    domain: str = tld.domain
    subdomain: str = tld.subdomain
    suffix: str = tld.suffix

    app.log(f"Trying to go to {subdomain}.{domain}.{suffix} {tld.is_private=}")

    if f"{domain}.{suffix}" == "reddit.com":
        page_result: PageResult = await handle_reddit(url=url, app=app)
    else:
        page_result: PageResult = await handle_unknown(url=url, app=app)
    return page_result


def create_error_page(url: str, error: str) -> PageResult:
    """Create an error page for display.

    Args:
        url (str): The URL that failed to load.
        error (str): The error message to display.

    Returns:
        PageResult: A page result with error information.
    """
    error_text: str = f"[red]Error[/red]\n\n[yellow]{url}[/yellow]\n\n{error}"
    error_widget = Static(error_text)
    return PageResult(
        url=url,
        title="Error",
        summary="Failed to load page",
        widgets=[error_widget],
    )


class Browser(ScrollableContainer):
    """This represents one browser tab."""

    def __init__(self, page_result: PageResult) -> None:
        super().__init__()
        self._page_result: PageResult = page_result

    def compose(self) -> ComposeResult:
        """Called by Textual to create child widgets.

        This method is called when a widget is mounted or by
        setting recompose=True when calling refresh()

        Yields:
            Iterator[ComposeResult]: The Widgets this browser tab will have.
        """
        if not self._page_result.widgets:
            yield Input(placeholder="Enter URL")
            yield Static("No page loaded")
        else:
            yield from self._page_result.widgets

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Gets triggered when Input() is submitted."""
        self.query_one(Static).update(f"Loaded: {event.value}")


class BrowserTab(TabPane):
    """A single tab in the browser."""

    def __init__(self, title: str, page_result: PageResult, tab_id: str | None = None) -> None:
        """Init the browser tab.

        Args:
            tab_id(str | None): Optional ID for the BrowserTab.
            title (str): Title of the TabPane (will be displayed in a tab label).
            page_result (PageResult): Represents the result of processing a web page.
        """
        super().__init__(title, id=tab_id)
        self.history: list[str] = []
        self._page_result: PageResult = page_result

    def compose(self) -> ComposeResult:
        """Called by Textual to create child widgets.

        Yields:
            One browser tab.
        """
        yield Browser(self._page_result)


class JuiceboxApp(App[None]):
    """Juicebox TUI web browser."""

    settings: BrowserSettings
    history_engine: Engine

    BINDINGS = get_hotkeys()
    CSS_PATH = "Juicebox.tcss"

    def compose(self) -> ComposeResult:  # noqa: PLR6301
        """Apply the UI layout.

        Layout consists of a header, a markdown content area, and a footer.

        Yields:
            ComposeResult: The UI components.

        """
        yield Header(show_clock=True, id="header", icon="🧃")

        yield Vertical(
            Input(placeholder="Enter a URL", id="url_input"),
            Button("Open in New Tab", id="new_tab_button"),
            id="input_container",
        )

        with TabbedContent(id="tabs"):
            yield TabPane(title="about:juicebox", id="about_juicebox")

        yield Footer(compact=True, id="footer")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Gets triggered when clicking buttons.

        Args:
            event (Button.Pressed): Event sent when a Button is pressed.
        """
        if event.button.id == "new_tab_button":
            await self.open_new_tab()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the input submission to trigger the button press."""
        if event.input.id == "url_input":
            await self.open_new_tab()

    async def open_new_tab(self) -> None:
        """Main logic to fetch content and create a tab."""
        url_input: Input = self.query_one("#url_input", Input)
        url: str = url_input.value

        if not url:
            return

        page_result: PageResult
        tab_title: str

        try:
            page_result = await fetch_site_contents(app=self, url=url)
            tab_title = url

            url_data: URLData = URLData(url=page_result.url, title=page_result.title, summary=page_result.summary)
            save_url_to_history(url_data=url_data, engine=self.history_engine, settings=self.settings)

            # Clear the input field for the next URL
            url_input.value = ""

        except BrowserError as e:
            self.bell()
            page_result = create_error_page(url=url, error=str(e))
            tab_title = f"Error: {url}"

        # Create the tab once with the appropriate page_result and title
        tabbed_content: TabbedContent = self.query_one(TabbedContent)
        new_tab_id: str = f"tab-{tabbed_content.tab_count + 1}-{abs(hash(url))}"

        new_tab = BrowserTab(title=tab_title, page_result=page_result, tab_id=new_tab_id)

        await tabbed_content.add_pane(new_tab)
        tabbed_content.active = new_tab_id

    async def close_active_tab(self) -> None:
        """Close the tab that is active."""
        # TODO(TheLovinator): Remove pane with ID instead of the active one.  # noqa: TD003

        tabs: TabbedContent = self.query_one(TabbedContent)
        await tabs.remove_pane(tabs.active)

    async def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_next_tab()

    async def action_previous_tab(self) -> None:
        """Switch to the previous tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()

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
            msg = "Current theme not found in available themes, switching to first theme."
            self.notify(message=msg, timeout=2, severity="error")

        next_theme_name: str = theme_names[next_index]
        self.theme = next_theme_name

        msg: str = f"Switched to theme: {next_theme_name} ({next_index + 1}/{len(theme_names)})"
        self.notify(msg, timeout=1)

    def action_toggle_image_method(self) -> None:
        """Toggle between image rendering methods."""
        methods: list[str] = ["auto", "tgp", "sixel", "unicode", "halfcell"]
        current: str = self.settings.image_method
        try:
            current_index: int = methods.index(current)
            next_index: int = (current_index + 1) % len(methods)
        except ValueError:
            next_index = 0

        next_method: str = methods[next_index]
        self.settings.image_method = next_method

        # Update environment variable so it's picked up on next fetch
        os.environ["JUICEBOX_IMAGE_METHOD"] = next_method
        self.notify(f"Image method: {next_method} ({next_index + 1}/{len(methods)})", timeout=2)

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.title = "Juicebox"

        # Load settings
        self.settings = BrowserSettings()

        # Apply theme from settings
        self.theme = self.settings.theme

        # Initialize history database engine
        self.history_engine = create_engine(str(self.settings.history_file_path), echo=False)
        SQLModel.metadata.create_all(self.history_engine)


app = JuiceboxApp()

if __name__ == "__main__":
    app.run()
