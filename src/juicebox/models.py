from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from textual.widget import Widget


class PageResult(BaseModel):
    """Represents the result of processing a web page.

    Attributes:
        url: The URL of the processed page.
        status: The HTTP status code returned by the page.
        markdown: The markdown representation of the page content.
        error: Optional error message if processing failed.

    """

    # Allow arbitrary widget types in `widgets` without requiring pydantic schemas
    model_config = ConfigDict(arbitrary_types_allowed=True)

    url: str = Field(
        ...,
        description="The URL of the processed page",
        min_length=1,
    )

    status: int = Field(
        ...,
        description="The HTTP status code returned by the page",
        ge=0,
        le=999,
    )

    markdown: str = Field(
        default="",
        description="The markdown representation of the page content",
    )

    widgets: list[Widget] = Field(
        default_factory=list[Widget],
        description="List of widgets associated with the page",
    )

    error: str | None = Field(
        default=None,
        description="Optional error message if processing failed",
    )

    @field_validator("url")
    @classmethod
    def validate_url_not_empty(cls, v: str) -> str:
        """Ensure URL is not empty or whitespace only.

        Args:
            v: The URL string to validate.

        Returns:
            The validated URL string.

        Raises:
            ValueError: If URL is empty or whitespace only.

        """
        if not v or not v.strip():
            msg = "URL cannot be empty"
            raise ValueError(msg)
        return v.strip()
