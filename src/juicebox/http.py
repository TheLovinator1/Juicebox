from typing import TYPE_CHECKING

from curl_cffi import AsyncSession
from curl_cffi import Session
from curl_cffi import requests

from juicebox.settings import BrowserSettings

if TYPE_CHECKING:
    from juicebox.app import JuiceboxApp
    from juicebox.settings import BrowserSettings


def request_head(url: str, app: JuiceboxApp) -> requests.Response:
    """Impersonate Firefox and do HEAD request.

    Args:
        url (str): The URL we want to check.
        app (JuiceboxApp): The Juicebox application instance.

    Returns:
        requests.Response: Contains information the server sends.
    """
    settings: BrowserSettings = app.settings
    with Session(
        allow_redirects=True,
        impersonate=settings.user_agent,
        timeout=settings.request_timeout,
    ) as s:
        resp: requests.Response = s.head(url)
        return resp


async def request_ahead(url: str, app: JuiceboxApp) -> requests.Response:
    """Impersonate Firefox and do HEAD request.

    Args:
        url (str): The URL we want to check.
        app (JuiceboxApp): The Juicebox application instance.

    Returns:
        requests.Response: Contains information the server sends.
    """
    settings: BrowserSettings = app.settings
    async with AsyncSession(
        allow_redirects=True,
        impersonate=settings.user_agent,
        timeout=settings.request_timeout,
    ) as s:
        resp: requests.Response = await s.head(url)
        return resp


def request_get(url: str, app: JuiceboxApp) -> requests.Response:
    """Impersonate Firefox and do GET request.

    Args:
        url (str): The URL we want to get.
        app (JuiceboxApp): The Juicebox application instance.

    Returns:
        requests.Response: Contains information the server sends.
    """
    settings: BrowserSettings = app.settings
    with Session(allow_redirects=True, impersonate=settings.user_agent, timeout=settings.request_timeout) as s:
        resp: requests.Response = s.get(url)
        return resp


async def request_aget(url: str, app: JuiceboxApp) -> requests.Response:
    """Impersonate Firefox and do GET request.

    Args:
        url (str): The URL we want to get.
        app (JuiceboxApp): The Juicebox application instance.

    Returns:
        requests.Response: Contains information the server sends.
    """
    settings: BrowserSettings = app.settings
    async with AsyncSession(
        allow_redirects=True,
        impersonate=settings.user_agent,
        timeout=settings.request_timeout,
    ) as s:
        resp: requests.Response = await s.get(url)
        return resp
