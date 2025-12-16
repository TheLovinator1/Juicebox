import json
from dataclasses import dataclass
from typing import Any
from typing import Literal
from typing import cast
from urllib.parse import ParseResult
from urllib.parse import urlparse

from curl_cffi import requests
from pydantic import BaseModel
from pydantic import ConfigDict

from juicebox.app import BrowserSettings
from juicebox.app import PageResult
from juicebox.interactions import interaction


class PostData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    approved_at_utc: float | None = None
    subreddit: str
    selftext: str
    author_fullname: str | None = None
    saved: bool
    mod_reason_title: str | None = None
    gilded: int
    clicked: bool
    title: str
    link_flair_richtext: list[Any]
    subreddit_name_prefixed: str
    hidden: bool
    pwls: int | None = None
    link_flair_css_class: str | None = None
    downs: int
    top_awarded_type: str | None = None
    hide_score: bool
    name: str
    quarantine: bool
    link_flair_text_color: str | None = None
    upvote_ratio: float
    author_flair_background_color: str | None = None
    subreddit_type: str
    ups: int
    total_awards_received: int
    media_embed: dict[str, Any]
    author_flair_template_id: str | None = None
    is_original_content: bool
    user_reports: list[Any]
    secure_media: dict[str, Any] | None = None
    is_reddit_media_domain: bool
    is_meta: bool
    category: str | None = None
    secure_media_embed: dict[str, Any]
    link_flair_text: str | None = None
    can_mod_post: bool
    score: int
    approved_by: str | None = None
    is_created_from_ads_ui: bool
    author_premium: bool
    thumbnail: str
    # 'edited' can be False (bool) or a timestamp (float) in Reddit's API
    edited: float | bool
    author_flair_css_class: str | None = None
    author_flair_richtext: list[Any]
    gildings: dict[str, int]
    content_categories: list[str] | None = None
    is_self: bool
    mod_note: str | None = None
    created: float
    link_flair_type: str
    wls: int | None = None
    removed_by_category: str | None = None
    banned_by: str | None = None
    author_flair_type: str | None = None
    domain: str
    allow_live_comments: bool
    selftext_html: str | None = None
    likes: bool | None = None
    suggested_sort: str | None = None
    banned_at_utc: float | None = None
    view_count: int | None = None
    archived: bool
    no_follow: bool
    is_crosspostable: bool
    pinned: bool
    over_18: bool
    all_awardings: list[Any]
    awarders: list[Any]
    media_only: bool
    link_flair_template_id: str | None = None
    can_gild: bool
    spoiler: bool
    locked: bool
    author_flair_text: str | None = None
    treatment_tags: list[str]
    visited: bool
    removed_by: str | None = None
    num_reports: int | None = None
    distinguished: str | None = None
    subreddit_id: str
    author_is_blocked: bool
    mod_reason_by: str | None = None
    removal_reason: str | None = None
    link_flair_background_color: str | None = None
    id: str
    is_robot_indexable: bool
    report_reasons: str | None = None
    author: str
    discussion_type: str | None = None
    num_comments: int
    send_replies: bool
    contest_mode: bool
    mod_reports: list[Any]
    author_patreon_flair: bool
    author_flair_text_color: str | None = None
    permalink: str
    stickied: bool
    url: str
    subreddit_subscribers: int
    created_utc: float
    num_crossposts: int
    media: dict[str, Any] | None = None
    is_video: bool


class Post(BaseModel):
    kind: str
    data: PostData


class ListingData(BaseModel):
    after: str | None = None
    dist: int
    modhash: str
    geo_filter: str | None = None
    children: list[Post]
    before: str | None = None


class RedditResponse(BaseModel):
    kind: str
    data: ListingData


@dataclass
class RedditPathComponents:
    subreddit: str | None
    post_id: str | None
    type: Literal["subreddit", "post", "home", "unknown"]


def create_markdown_for_post(post: Post) -> str:
    """Convert a Reddit post to a markdown representation.

    Args:
        post: The Reddit Post object.

    Returns:
        A markdown string representing the post.
    """
    md_lines: list[str] = []

    # Title and byline
    md_lines.extend((
        f"## {post.data.title}",
        f"*Posted by u/{post.data.author} in r/{post.data.subreddit}*",
        "",
    ))

    # Selftext (if any)
    if post.data.selftext:
        md_lines.extend((post.data.selftext, ""))

    # Link (if not a self post)
    if not post.data.is_self:
        md_lines.extend((
            f"**Link:** {post.data.url}",
            "",
        ))

    # Footer with score and comments
    md_lines.append(
        f"👍 {post.data.score} | 💬 {post.data.num_comments} | "
        f"[View on Reddit](https://reddit.com{post.data.permalink})",
    )

    return "\n".join(md_lines)


def create_markdown_for_listing(
    listing: RedditResponse,
    subreddit: str | None = None,
) -> str:
    """Convert a Reddit listing to a markdown representation.

    Args:
        listing: The RedditResponse object containing the listing.
        subreddit: Optional subreddit name for the header.

    Returns:
        A markdown string representing the listing.
    """
    md_lines: list[str] = []

    # Add subreddit header if provided
    if subreddit:
        md_lines.extend((
            f"# r/{subreddit}",
            "",
        ))
    elif listing.data.children:
        # Try to get subreddit from first post
        first_subreddit = listing.data.children[0].data.subreddit
        if first_subreddit:
            md_lines.extend((
                f"# r/{first_subreddit}",
                "",
            ))

    # Add posts
    for i, post in enumerate(listing.data.children):
        if i > 0:
            md_lines.append("\n---\n")
        md_lines.append(create_markdown_for_post(post))

    return "\n".join(md_lines)


def get_reddit_path(url: str) -> RedditPathComponents:  # noqa: PLR0911
    """Extract the Reddit path from a URL.

    Also handles these domains:
    - www.reddit.com
    - old.reddit.com

    Example URLs:
    - https://old.reddit.com/r/Games/
    - https://old.reddit.com/
    - https://old.reddit.com/r/Games/comments/1lqa2hj/has_xbox_considered_laying_one_person_off_instead/

    Args:
        url: The full Reddit URL.

    Returns:
        A RedditPathComponents object with extracted parts.
    """
    # Parse URL into components
    parsed: ParseResult = urlparse(url)

    # Normalize and split the path into segments
    path: str = parsed.path or "/"
    parts: list[str] = [p for p in path.split("/") if p]

    # Root/home page like https://old.reddit.com/ or https://www.reddit.com/
    if not parts:
        return RedditPathComponents(subreddit=None, post_id=None, type="home")

    # Handle patterns:
    # - /r/<subreddit>/
    # - /r/<subreddit>/comments/<post_id>/...
    if parts[0] == "r":
        # If subreddit not present for some reason, mark as failure
        if len(parts) < 2:  # noqa: PLR2004
            return RedditPathComponents(subreddit=None, post_id=None, type="unknown")

        subreddit: str = parts[1]

        # Post pattern under subreddit
        if len(parts) >= 3 and parts[2] == "comments":  # noqa: PLR2004
            post_id: str | None = parts[3] if len(parts) >= 4 and parts[3] else None  # noqa: PLR2004
            if post_id:
                return RedditPathComponents(
                    subreddit=subreddit,
                    post_id=post_id,
                    type="post",
                )
            # If comments without id, fall back to subreddit context
            return RedditPathComponents(
                subreddit=subreddit,
                post_id=None,
                type="subreddit",
            )

        # Otherwise it's a subreddit listing
        return RedditPathComponents(
            subreddit=subreddit,
            post_id=None,
            type="subreddit",
        )

    # Support top-level comments route: /comments/<post_id>/...
    if parts[0] == "comments":
        post_id = parts[1] if len(parts) >= 2 else None  # noqa: PLR2004
        return RedditPathComponents(
            subreddit=None,
            post_id=post_id,
            type="post" if post_id else "unknown",
        )

    # Fail if no known pattern matched; tell the browser to use default handling
    return RedditPathComponents(subreddit=None, post_id=None, type="unknown")


def _get_json_url(comps: RedditPathComponents) -> str | None:
    """Get the JSON API URL for a Reddit path.

    Args:
        comps: Parsed path components from the Reddit URL.

    Returns:
        The JSON API URL, or None if it cannot be determined.

    """
    base = "https://old.reddit.com"
    if comps.type == "home":
        return f"{base}/.json"
    if comps.type == "subreddit" and comps.subreddit:
        return f"{base}/r/{comps.subreddit}.json"
    if comps.type == "post" and comps.post_id:
        if comps.subreddit:
            return f"{base}/r/{comps.subreddit}/comments/{comps.post_id}.json"
        return f"{base}/comments/{comps.post_id}.json"
    return None


@interaction("reddit.com")
def handle_reddit(url: str, settings: BrowserSettings) -> PageResult:  # noqa: PLR0911
    """Handle Reddit URLs by fetching JSON API endpoint.

    Converts standard Reddit URLs to the .json endpoint and fetches data
    from the official Reddit JSON API. Supports both subreddit listings
    and individual posts.

    Args:
        url: The Reddit URL to fetch.
        settings: Browser settings to use.

    Returns:
        A PageResult containing the processed Reddit content.

    """
    # Determine the appropriate JSON endpoint from the provided URL
    comps: RedditPathComponents = get_reddit_path(url)
    json_url: str | None = _get_json_url(comps)

    if json_url is None:
        # Fail if we can't determine a valid JSON URL
        return PageResult(
            url=url,
            status=0,
            markdown="",
            error="Could not determine Reddit JSON endpoint from URL.",
        )

    try:
        # Fetch from Reddit's JSON API
        response: requests.Response = requests.get(
            json_url,
            timeout=settings.request_timeout,
            impersonate=settings.user_agent,
        )

        http_ok = 200
        if response.status_code != http_ok:
            error_msg: str = f"Reddit API returned status {response.status_code}"
            return PageResult(
                url=url,
                status=response.status_code,
                markdown="",
                error=error_msg,
            )

        # Try to convert API response into readable markdown
        rendered: str | None = None
        try:
            data_raw: object = json.loads(response.text or "null")
            data = cast("dict[str, Any] | list[dict[str, Any]]", data_raw)
            rendered = _render_reddit_markdown(comps, data)
        except json.JSONDecodeError as e:
            # Invalid JSON response
            json_error: str = f"Reddit API returned invalid JSON: {e}"
            return PageResult(
                url=url,
                status=response.status_code,
                markdown="",
                error=json_error,
            )
        except ValueError as e:
            # Validation error from Pydantic
            validation_error: str = f"Failed to parse Reddit response: {e}"
            return PageResult(
                url=url,
                status=response.status_code,
                markdown="",
                error=validation_error,
            )

        if rendered is not None:
            return PageResult(
                url=url,
                status=response.status_code,
                markdown=rendered,
            )

        # If rendering returned None (unexpected data structure), show the raw JSON
        # This shouldn't happen as _render_reddit_markdown raises ValueError
        md_fallback: str = "```json\n" + (response.text or "") + "\n```"
        return PageResult(
            url=url,
            status=response.status_code,
            markdown=md_fallback,
        )
    except (OSError, ValueError, KeyError) as e:
        # OSError: network errors, ValueError: JSON/validation, KeyError structure
        return PageResult(url=url, status=0, markdown="", error=str(e))


def _render_reddit_markdown(
    comps: RedditPathComponents,
    data: dict[str, Any] | list[dict[str, Any]],
) -> str | None:
    """Render Reddit JSON to markdown if possible.

    Args:
        comps: Parsed path components for the original URL.
        data: Parsed JSON payload from Reddit.

    Returns:
        A markdown string if rendering succeeded, otherwise None.

    Raises:
        ValueError: If the data structure doesn't match expected format.

    """
    # Subreddit/home listings return a single Listing object
    if comps.type in {"home", "subreddit"} and isinstance(data, dict):
        try:
            listing: RedditResponse = RedditResponse.model_validate(data)
            return create_markdown_for_listing(listing, comps.subreddit)
        except Exception as e:
            msg = f"Failed to parse subreddit/home listing: {e}"
            raise ValueError(msg) from e

    # Post pages usually return a list where the first item is the post Listing
    if comps.type == "post" and isinstance(data, list) and data:
        try:
            first: dict[str, Any] = data[0]
            listing0: RedditResponse = RedditResponse.model_validate(first)
            if listing0.data.children:
                return create_markdown_for_post(listing0.data.children[0])
        except Exception as e:
            msg = f"Failed to parse post listing: {e}"
            raise ValueError(msg) from e

    return None


__all__: list[str] = [
    "handle_reddit",
]
