from pydantic import BaseModel

from .blame_line_range_dto import BlameLineRangeDto
from .pull_request_info_dto import PullRequestInfoDto


class BlameCommitDto(BaseModel):
    """DTO for commit information from GitHub blame results."""

    sha: str
    message: str
    author: str
    author_email: str | None = None
    author_login: str | None = None
    timestamp: str
    url: str
    additions: int | None = None
    deletions: int | None = None
    line_ranges: list[BlameLineRangeDto]
    pr_info: PullRequestInfoDto | None = None

    class Config:
        frozen = True
