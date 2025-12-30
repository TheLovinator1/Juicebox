from typing import TYPE_CHECKING
from typing import ClassVar
from typing import Never
from typing import Self

import pytest

from juicebox.http import request_head

if TYPE_CHECKING:
    from types import TracebackType

    from curl_cffi import Response


def test_request_head_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        status_code = 200
        headers: ClassVar[dict[str, str]] = {"Content-Type": "text/html"}
        url: str = "https://example.com"

    class DummySession:
        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            pass

        def head(self, url: str) -> DummyResponse:  # noqa: PLR6301
            assert url == "https://example.com"
            return DummyResponse()

    import juicebox.http as http_mod  # noqa: PLC0415

    monkeypatch.setattr(http_mod, "Session", lambda **kwargs: DummySession())  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]  # noqa: ARG005
    resp: Response = request_head("https://example.com")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"] == "text/html"
    assert resp.url == "https://example.com"


def test_request_head_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummySession:
        def __enter__(self) -> Self:
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            exc_tb: TracebackType | None,
        ) -> None:
            pass

        def head(self, url: str) -> Never:  # noqa: ARG002, PLR6301
            msg = "Network error"
            raise RuntimeError(msg)

    import juicebox.http as http_mod  # noqa: PLC0415

    monkeypatch.setattr(http_mod, "Session", lambda **kwargs: DummySession())  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]  # noqa: ARG005
    with pytest.raises(RuntimeError, match="Network error"):
        request_head("https://fail.example.com")
