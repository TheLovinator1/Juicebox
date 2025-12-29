from curl_cffi import AsyncSession
from curl_cffi import Session
from curl_cffi import requests


def request_head(url: str) -> requests.Response:
    """Impersonate Firefox and do HEAD request.

    Args:
        url (str): The URL we want to check.

    Returns:
        requests.Response: Contains information the server sends.
    """
    with Session(allow_redirects=True, impersonate="firefox", timeout=10) as s:
        resp: requests.Response = s.head(url)
        return resp


async def request_ahead(url: str) -> requests.Response:
    """Impersonate Firefox and do HEAD request.

    Args:
        url (str): The URL we want to check.

    Returns:
        requests.Response: Contains information the server sends.
    """
    async with AsyncSession(
        allow_redirects=True,
        impersonate="firefox",
        timeout=10,
    ) as s:
        resp: requests.Response = await s.head(url)
        return resp


def request_get(url: str) -> requests.Response:
    """Impersonate Firefox and do GET request.

    Args:
        url (str): The URL we want to get.

    Returns:
        requests.Response: Contains information the server sends.
    """
    with Session(allow_redirects=True, impersonate="firefox", timeout=10) as s:
        resp: requests.Response = s.get(url)
        return resp


async def request_aget(url: str) -> requests.Response:
    """Impersonate Firefox and do GET request.

    Args:
        url (str): The URL we want to get.

    Returns:
        requests.Response: Contains information the server sends.
    """
    async with AsyncSession(
        allow_redirects=True,
        impersonate="firefox",
        timeout=10,
    ) as s:
        resp: requests.Response = await s.get(url)
        return resp
