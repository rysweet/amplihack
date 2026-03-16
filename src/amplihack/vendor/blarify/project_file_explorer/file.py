import os
from amplihack.utils.logging_utils import log_call


class File:
    name: str
    root_path: str
    level: int

    @log_call
    def __init__(self, name: str, root_path: str, level: int):
        self.name = name
        self.root_path = root_path
        self.level = level

    @property
    @log_call
    def path(self) -> str:
        return os.path.join(self.root_path, self.name)

    @property
    @log_call
    def extension(self) -> str:
        return os.path.splitext(self.name)[1]

    @property
    @log_call
    def uri_path(self) -> str:
        return "file://" + self.path

    @log_call
    def __str__(self) -> str:
        return self.get_path()
