import datetime
import json
from typing import TYPE_CHECKING

from pydantic import BaseModel
from sqlmodel import Field
from sqlmodel import Session
from sqlmodel import SQLModel
from sqlmodel import select

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import Engine
    from sqlmodel.sql.expression import SelectOfScalar

    from juicebox.settings import BrowserSettings


class HistoryEntry(SQLModel, table=True):
    """A history entry representing a visited URL."""

    id: int | None = Field(default=None, primary_key=True, description="Primary key.")

    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Timestamp of when the entry was created. Stored in UTC.",
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC),
        description="Timestamp of when the entry was last updated. Stored in UTC.",
    )

    date_visited_json: str = Field(
        default="[]",
        description="JSON-encoded list of timestamps when the URL was visited.",
    )

    @property
    def date_visited(self) -> list[datetime.datetime]:
        """Get the list of visit timestamps as datetime objects."""
        return [datetime.datetime.fromisoformat(dt) for dt in json.loads(self.date_visited_json)]

    @date_visited.setter
    def date_visited(self, value: list[datetime.datetime]) -> None:
        """Set the list of visit timestamps from datetime objects."""
        self.date_visited_json = json.dumps([dt.isoformat() for dt in value])

    # Screenshot data
    screenshot: bytes | None = Field(default=None, description="Screenshot of the webpage at the time of visit.")
    screenshot_date: datetime.datetime | None = Field(default=None, description="When captured.")

    # Page metadata
    url: str = Field(index=True, unique=True, description="The URL visited.")
    title: str = Field(description="The title of the page.")
    summary: str = Field(description="A short summary or description of the page.")

    # Favicon data
    favicon: bytes | None = Field(default=None, description="Favicon of the webpage at the time of visit")
    favicon_date: datetime.datetime | None = Field(default=None, description="Timestamp of when the favicon was saved.")

    def normalized_url(self) -> str:
        """Return a normalized version of the URL for comparison.

        This removes the scheme (http, https) and www prefix.

        Returns:
            The normalized URL.

        """
        url: str = self.url.lower()
        if url.startswith("http://"):
            url = url[len("http://") :]
        elif url.startswith("https://"):
            url = url[len("https://") :]
        return url.removeprefix("www.")


class URLData(BaseModel):
    """Data for a URL to be saved to history."""

    url: str
    title: str = ""
    summary: str = ""


def remove_expired_history(session: Session, settings: BrowserSettings) -> None:
    """Clean up old history entries based on settings.

    Args:
        session: Database session to use.
        settings: Browser settings to use.

    """
    cutoff_date: datetime.datetime = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        days=settings.history_days,
    )

    statement: SelectOfScalar[HistoryEntry] = select(HistoryEntry).where(HistoryEntry.updated_at < cutoff_date)
    old_entries: Sequence[HistoryEntry] = session.exec(statement).all()

    for entry in old_entries:
        session.delete(entry)

    session.commit()


def save_or_update_history_entry(url_data: URLData, now: datetime.datetime, session: Session) -> None:
    """Insert or update a history entry for the given URL data.

    Args:
        url_data: URL data to insert or update.
        now: Current timestamp.
        session: Database session to use.
    """
    statement: SelectOfScalar[HistoryEntry] = select(HistoryEntry).where(HistoryEntry.url == url_data.url)
    existing_entry: HistoryEntry | None = session.exec(statement).first()

    if existing_entry:
        visits: list[datetime.datetime] = existing_entry.date_visited
        visits.append(now)
        existing_entry.date_visited = visits
        existing_entry.updated_at = now
        session.add(existing_entry)

    else:
        new_entry = HistoryEntry(
            url=url_data.url,
            title=url_data.title,
            summary=url_data.summary,
            created_at=now,
            updated_at=now,
        )
        new_entry.date_visited = [now]
        session.add(new_entry)

    session.commit()


def save_url_to_history(url_data: URLData, engine: Engine, settings: BrowserSettings) -> None:
    """Save a URL to the history file.

    URLs are stored with newest first. Duplicates are removed (moved to top).
    Maximum URLs kept is determined by settings.history_limit.

    Args:
        url_data: URL data to save.
        engine: Database engine to use.
        settings: Browser settings to use.

    """
    now: datetime.datetime = datetime.datetime.now(datetime.UTC)

    with Session(engine) as session:
        save_or_update_history_entry(url_data=url_data, now=now, session=session)
        remove_expired_history(session=session, settings=settings)


def get_matching_history(query: str, engine: Engine, limit: int = 10) -> list[HistoryEntry]:
    """Get history entries matching the given query.

    Matches against URL and title, ordered by most recent first.

    Args:
        query: The search query string.
        engine: Database engine to use.
        limit: Maximum number of results to return.

    Returns:
        List of matching history entries, ordered by most recent.
    """
    with Session(engine) as session:
        # Get all entries
        statement: SelectOfScalar[HistoryEntry] = select(HistoryEntry)
        all_entries: Sequence[HistoryEntry] = session.exec(statement).all()

        # Filter in Python to match query in URL or title (case-insensitive)
        if not query:
            matching: list[HistoryEntry] = list(all_entries)
        else:
            query_lower: str = query.lower()
            matching: list[HistoryEntry] = []
            for entry in all_entries:
                entry_url: str = entry.url.lower()
                entry_title: str = entry.title.lower()

                if query_lower in entry_url or query_lower in entry_title:
                    matching.append(entry)

        # Return the most recent entries (sorted by updated_at descending)
        sorted_entries: list[HistoryEntry] = sorted(matching, key=lambda e: e.updated_at, reverse=True)
        return sorted_entries[:limit]
