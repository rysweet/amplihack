import os
from collections.abc import Iterator

from .file import File
from .folder import Folder


class ProjectFilesIterator:
    root_path: str
    paths_to_skip: list[str]
    names_to_skip: list[str]
    extensions_to_skip: list[str]
    max_file_size_mb: float

    def __init__(
        self,
        root_path: str,
        paths_to_skip: list[str] | None = None,
        names_to_skip: list[str] | None = None,
        extensions_to_skip: list[str] | None = None,
        blarignore_path: str | None = None,
        max_file_size_mb: float = 0.8,
    ):
        self.paths_to_skip = paths_to_skip or []
        self.root_path = root_path
        self.names_to_skip = names_to_skip or []
        self.extensions_to_skip = extensions_to_skip or []
        self.max_file_size_mb = max_file_size_mb

        if blarignore_path:
            ignored_files = self.get_ignore_files(blarignore_path)
            self.names_to_skip.extend(ignored_files)

    def get_ignore_files(self, gitignore_path: str) -> list[str]:
        if not os.path.exists(gitignore_path):
            return []
        with open(gitignore_path) as f:
            return [line.strip() for line in f.readlines()]

    def __iter__(self) -> Iterator[Folder]:
        for current_path, dirs, files in os.walk(self.root_path, topdown=True):
            dirs[:] = self._get_filtered_dirs(current_path, dirs)
            level = self.get_path_level_relative_to_root(current_path)
            files = self._get_filtered_files(current_path, files, level + 1)
            folders = self.empty_folders_from_dirs(current_path, dirs, level + 1)
            name = (
                self.get_base_name(current_path)
                if not current_path.endswith("/")
                else self.get_base_name(current_path.rstrip("/"))
            )

            if not self._should_skip(current_path):
                yield Folder(
                    name=name,
                    path=current_path,
                    files=files,
                    folders=folders,
                    level=level,
                )

    def _get_filtered_dirs(self, root: str, dirs: list[str]) -> list[str]:
        dirs = [dir for dir in dirs if not self._should_skip(os.path.join(root, dir))]
        return dirs

    def get_path_level_relative_to_root(self, path: str) -> int:
        level = path.count(os.sep) - self.root_path.count(os.sep)
        return level

    def _get_filtered_files(self, root: str, files: list[str], level: int) -> list[File]:
        files = [file for file in files if not self._should_skip(os.path.join(root, file))]

        return [File(name=file, root_path=root, level=level) for file in files]

    def empty_folders_from_dirs(self, root: str, dirs: list[str], level: int) -> list[Folder]:
        return [
            Folder(
                name=dir,
                path=os.path.join(root, dir),
                files=[],
                folders=[],
                level=level,
            )
            for dir in dirs
        ]

    def _should_skip(self, path: str) -> bool:
        is_basename_in_names_to_skip = os.path.basename(path) in self.names_to_skip

        is_path_in_paths_to_skip = any(
            path.startswith(path_to_skip) for path_to_skip in self.paths_to_skip
        )

        is_file_size_too_big = os.path.getsize(path) > self._mb_to_bytes(self.max_file_size_mb)

        is_extension_to_skip = any(
            path.endswith(extension) for extension in self.extensions_to_skip
        )

        return (
            is_basename_in_names_to_skip
            or is_path_in_paths_to_skip
            or is_file_size_too_big
            or is_extension_to_skip
        )

    def _mb_to_bytes(self, mb: float) -> float:
        return 1024 * 1024 * mb

    def get_base_name(self, current_path: str) -> str:
        return os.path.basename(current_path)
