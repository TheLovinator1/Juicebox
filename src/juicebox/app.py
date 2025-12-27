from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Literal
from typing import cast

import tldextract
from textual.app import App
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.theme import Theme
from textual.widgets import Footer
from textual.widgets import Header
from textual.widgets import Input
from textual.widgets import Markdown
from textual.widgets import Tab
from textual.widgets import Tabs

from juicebox.history import URLSuggester
from juicebox.history import save_url_to_history
from juicebox.hotkeys import get_hotkeys
from juicebox.settings import BrowserSettings
from juicebox.sites.reddit import handle_reddit
from juicebox.sites.unknown import handle_unknown

if TYPE_CHECKING:
    from textual.theme import Theme

    from juicebox.models import PageResult


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
        page_result: PageResult = await handle_reddit(url=url)
    else:
        page_result: PageResult = await handle_unknown(url=url)
    return page_result


class JuiceboxApp(App[None]):
    """Juicebox TUI web browser.

    Allows typing a domain/URL, fetches the page, converts to Markdown,
    and displays it in a scrollable pane.
    """

    current_page: PageResult | None = None
    markdown: Markdown
    current_tabs: int = 1
    settings: BrowserSettings
    tab_content: dict[str, PageResult | None]  # Maps tab ID to PageResult

    BINDINGS = get_hotkeys()
    CSS_PATH = "Juicebox.tcss"

    def _get_active_tab_id(self) -> str | None:
        """Get the ID of the currently active tab.

        Returns:
            The active tab ID, or None if no tab is active.
        """
        tabs: Tabs = self.query_one(Tabs)
        active_tab: Tab | None = tabs.active_tab
        return active_tab.id if active_tab else None

    async def _update_markdown_from_tab(self) -> None:
        """Update the content display to show the current tab's content."""
        tab_id: str | None = self._get_active_tab_id()
        if not tab_id:
            return

        pr: PageResult | None = self.tab_content.get(tab_id)
        if pr:
            self.current_page = pr
            if pr.error:
                content: str = f"# Error {pr.status} for {pr.url}\n\n{pr.error}\n"
                await self.markdown.update(content)

                # Clear any widget content
                # TODO(TheLovinator): Check why we have this  # noqa: TD003
                widgets_container: VerticalScroll = self.query_one(
                    selector="#content_widgets",
                    expect_type=VerticalScroll,
                )

                await widgets_container.remove_children()
            # If widgets are present, render them; otherwise fallback to markdown
            elif pr.widgets:
                # TODO(TheLovinator): Check why we have this  # noqa: TD003
                widgets_container = self.query_one(
                    "#content_widgets",
                    VerticalScroll,
                )
                widgets_container.remove_children()

                for w in pr.widgets:
                    widgets_container.mount(w)

                self.markdown.update("")

            else:
                self.markdown.update(pr.markdown)

            self.title = f"Juicebox - {pr.url}"
            self.sub_title = f"Status: {pr.status}"
        else:
            self.current_page = None
            self.markdown.update("")
            self.title = "Juicebox"
            self.sub_title = "about:juicebox"

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

    async def action_new_tab(self) -> None:
        """Open a new tab."""
        tabs: Tabs = self.query_one(Tabs)
        self.current_tabs += 1
        new_tab: Tab = Tab(f"Tab {self.current_tabs}")
        tabs.add_tab(new_tab)

        # Initialize empty content for the new tab and immediately focus it
        new_tab_id: str | None = new_tab.id
        if new_tab_id:
            self.tab_content[new_tab_id] = None

            async def activate_and_prompt(attempt: int = 0) -> None:
                try:
                    tabs.active = new_tab_id
                except ValueError:
                    # Tab may not be mounted yet; retry a few times.
                    max_activation_attempts: int = 3
                    if attempt < max_activation_attempts:
                        self.call_after_refresh(
                            lambda: activate_and_prompt(attempt + 1),
                        )
                    return

                await self._update_markdown_from_tab()
                self.action_open_url()

            self.call_after_refresh(activate_and_prompt)

    async def action_close_tab(self) -> None:
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
            await self._update_markdown_from_tab()

    async def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_next_tab()
        await self._update_markdown_from_tab()

    async def action_previous_tab(self) -> None:
        """Switch to the previous tab."""
        tabs: Tabs = self.query_one(Tabs)
        tabs.action_previous_tab()
        await self._update_markdown_from_tab()

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

    async def on_tabs_tab_activated(self) -> None:
        """Handle tab activation (switching tabs)."""
        await self._update_markdown_from_tab()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle URL input submission.

        Args:
            event: The input submitted event.

        """
        url: str = event.value.strip()
        self.sub_title = f"Fetching {url}..."
        self.refresh(layout=True)

        page_result: PageResult = await fetch_site_contents(app=app, url=url)

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
