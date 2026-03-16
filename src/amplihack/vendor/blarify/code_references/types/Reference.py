from dataclasses import dataclass
from urllib.parse import unquote
from amplihack.utils.logging_utils import log_call


@dataclass
class Point:
    line: int
    character: int

    @log_call
    def __eq__(self, value):
        if not isinstance(value, Point):
            return False
        return self.line == value.line and self.character == value.character


@dataclass
class Range:
    start: Point
    end: Point

    @log_call
    def __eq__(self, value):
        if not isinstance(value, Range):
            return False
        return self.start == value.start and self.end == value.end


@dataclass
class Reference:
    range: Range
    uri: str

    @log_call
    def __init__(self, reference: dict = None, range: Range = None, uri: str = None):
        if range and uri:
            self.range = range
            self.uri = self._desencode_uri(uri)

        elif reference:
            self._initialize_from_dict(reference)

        else:
            raise ValueError("Invalid Reference initialization")

    @log_call
    def _initialize_from_dict(self, reference: dict) -> Range:
        self.range = Range(
            Point(reference["range"]["start"]["line"], reference["range"]["start"]["character"]),
            Point(reference["range"]["end"]["line"], reference["range"]["end"]["character"]),
        )

        uri = reference["uri"]
        self.uri = self._desencode_uri(uri)

    @log_call
    def _desencode_uri(self, uri: str) -> str:
        return unquote(uri)

    @property
    @log_call
    def start_dict(self) -> dict:
        return {"line": self.range.start.line, "character": self.range.start.character}

    @property
    @log_call
    def end_dict(self) -> dict:
        return {"line": self.range.end.line, "character": self.range.end.character}

    @log_call
    def __eq__(self, value):
        if isinstance(value, Reference):
            return self.range == value.range and self.uri == value.uri
        return False
