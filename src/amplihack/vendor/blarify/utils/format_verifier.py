from amplihack.utils.logging_utils import log_call
class FormatVerifier:
    @staticmethod
    @log_call
    def is_path_uri(path: str) -> bool:
        return path.startswith("file://") or path.startswith("integration://")
