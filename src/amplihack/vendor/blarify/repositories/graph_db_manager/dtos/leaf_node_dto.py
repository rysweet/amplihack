from pydantic import BaseModel


class LeafNodeDto(BaseModel):
    id: str
    name: str
    labels: list[str]
    path: str
    start_line: int | None
    end_line: int | None
    content: str

    def as_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "labels": self.labels,
            "path": self.path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "content": self.content,
        }
