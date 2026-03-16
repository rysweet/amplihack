import os
from amplihack.utils.logging_utils import log_call


class PathCalculator:
    @staticmethod
    @log_call
    def uri_to_path(uri: str) -> str:
        """Converts a URI to a file system path."""
        return uri.replace("file://", "")

    @staticmethod
    @log_call
    def extract_last_directory(path: str) -> str:
        """Extracts the last directory from a given path and formats it with surrounding slashes."""
        last_directory = os.path.basename(os.path.normpath(path))
        return f"/{last_directory}/"

    @staticmethod
    @log_call
    def compute_relative_path_with_prefix(pure_path: str, root_path: str) -> str:
        """Computes a relative path prefixed with the last directory of the root path."""
        last_dir = PathCalculator.extract_last_directory(root_path)
        relative_path = os.path.relpath(pure_path, root_path)
        return f"{last_dir}{relative_path}"

    @staticmethod
    @log_call
    def get_parent_folder_path(file_path):
        return "/".join(file_path.split("/")[:-1])

    @staticmethod
    @log_call
    def get_relative_path_from_uri(root_uri: str, uri: str) -> str:
        root_path = PathCalculator.uri_to_path(root_uri)
        path = PathCalculator.uri_to_path(uri)

        return os.path.relpath(path, root_path)
