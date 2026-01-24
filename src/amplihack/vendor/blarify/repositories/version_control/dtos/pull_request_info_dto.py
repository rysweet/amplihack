from pydantic import BaseModel


class PullRequestInfoDto(BaseModel):
    """DTO for pull request information from blame results."""

    number: int
    title: str
    url: str
    author: str | None = None
    merged_at: str | None = None
    state: str = "MERGED"
    body_text: str | None = None  # PR description from bodyText GraphQL field

    class Config:
        frozen = True
