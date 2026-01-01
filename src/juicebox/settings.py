from typing import TYPE_CHECKING

from curl_cffi import BrowserTypeLiteral  # noqa: TC002
from platformdirs import user_config_path
from platformdirs import user_data_path
from pydantic import AnyUrl
from pydantic import Field
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict
from textual.theme import BUILTIN_THEMES

if TYPE_CHECKING:
    from pathlib import Path

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

DEFAULT_HISTORY_DB_PATH: Path = DATA_DIR / "history.sqlite"
SQLITE_HISTORY_URL: AnyUrl = AnyUrl(url=f"sqlite:///{DEFAULT_HISTORY_DB_PATH}")


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

    # Look and feel settings
    theme: str = Field(default="textual-dark", description="Default theme for the browser", validate_default=True)

    # Terminal graphics protocol is was Kitty and friends uses so that is what we default to
    image_method: str = Field(default="tgp", description="Image rendering method for textual-image.")

    # History settings
    history_file_path: AnyUrl = Field(default=SQLITE_HISTORY_URL, description="Path to the SQLite database")
    history_days: int = Field(default=365 * 10, gt=0, description="Maximum age of history entries in days")
    history_store_nsfw: bool = Field(default=True, description="Whether to store NSFW pages in history")

    # Network settings
    request_timeout: int = Field(default=300, gt=0, description="HTTP request timeout in seconds")
    user_agent: BrowserTypeLiteral = Field(default="firefox", description="Browser to impersonate for curl_cffi")

    @model_validator(mode="after")
    def validate_theme(self) -> BrowserSettings:
        """Validate that the selected theme is valid.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If the theme is not valid.
        """
        themes: list[str] = list(BUILTIN_THEMES.keys())
        if self.theme not in themes:
            msg: str = f"Theme '{self.theme}' is not a valid theme. Available themes: {themes}"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_history_file_path(self) -> BrowserSettings:
        """Validate that the history file path is a SQLite database.

        Returns:
            The validated settings instance.

        Raises:
            ValueError: If the history file path is not a SQLite database.
        """
        if not str(self.history_file_path).startswith("sqlite:///"):
            msg: str = "History file path must be a SQLite database (sqlite:///...)"
            raise ValueError(msg)
        return self
