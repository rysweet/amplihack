from .file import File
from amplihack.utils.logging_utils import log_call


class Folder:
    name: str
    path: str

    @log_call
    def __init__(
        self, name: str, path: str, files: list[File], folders: list["Folder"], level: int
    ):
        self.name = name
        self.path = path
        self.files = files
        self.folders = folders
        self.level = level

    @property
    @log_call
    def uri_path(self) -> str:
        return "file://" + self.path

    @log_call
    def __str__(self) -> str:
        to_return = f"{self.path}\n"
        for file in self.files:
            to_return += f"\t{file}\n"
        for folder in self.folders:
            to_return += f"\t{folder}\n"

        return to_return
