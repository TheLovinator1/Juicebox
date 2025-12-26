from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from curl_cffi import BrowserTypeLiteral  # noqa: TC002
from platformdirs import user_config_path
from platformdirs import user_data_path
from pydantic import Field
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict

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

    # TODO(TheLovinator): We should make our own auto that picks the best available  # noqa: E501, TD003
    image_method: Literal["auto", "tgp", "sixel", "unicode", "halfcell"] = Field(
        default="tgp",
        description="Image rendering method for textual-image (auto, tgp, sixel, unicode, halfcell)",  # noqa: E501
    )
