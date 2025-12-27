from curl_cffi import AsyncSession
from curl_cffi import requests


async def request_get(url: str) -> requests.Response:
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
