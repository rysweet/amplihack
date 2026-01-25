from pydantic import BaseModel


class NodeWithContentDto(BaseModel):
    """DTO for nodes with full content, used in recursive DFS processing."""

    id: str
    name: str
    labels: list[str]
    path: str
    start_line: int | None = None
    end_line: int | None = None
    content: str = ""
    relationship_type: str | None = None  # Used when retrieved as a child

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "labels": self.labels,
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
            "relationship_type": self.relationship_type,
        }
