from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from juicebox.exceptions import BrowserError
from juicebox.models import PageResult
from juicebox.sites.unknown import handle_unknown


@pytest.mark.asyncio
async def test_handle_unknown_success(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    # Mock response object
    mock_response = MagicMock()
    mock_response.ok = True
    mock_response.text = "<h1>Hello</h1>"
    mock_response.url = "https://example.com"

    # Patch request_aget to return mock_response, markdownify, and Markdown widget in a single with statement  # noqa: E501
    with (
        patch(
            "juicebox.sites.unknown.request_aget",
            new=AsyncMock(return_value=mock_response),
        ),
        patch("juicebox.sites.unknown.markdownify", return_value="# Hello") as md_mock,
        patch(
            "juicebox.sites.unknown.Markdown",
            side_effect=lambda markdown: f"Widget({markdown})",  # type: ignore[no-untyped-def]
        ) as mw_mock,
    ):
        result = await handle_unknown("https://example.com")
        assert isinstance(result, PageResult)
        assert result.url == "https://example.com"
        assert result.widgets == ["Widget(# Hello)"]
        md_mock.assert_called_once_with("<h1>Hello</h1>")
        mw_mock.assert_called_once_with(markdown="# Hello")


@pytest.mark.asyncio
async def test_handle_unknown_failure(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: ARG001
    # Mock response object with not ok
    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.text = "fail"
    mock_response.url = "https://fail.com"

    with patch(
        "juicebox.sites.unknown.request_aget",
        new=AsyncMock(return_value=mock_response),
    ):
        with pytest.raises(BrowserError) as excinfo:
            await handle_unknown("https://fail.com")
        assert "Failed to access" in str(excinfo.value)
        assert "url='https://fail.com'" in str(excinfo.value)
