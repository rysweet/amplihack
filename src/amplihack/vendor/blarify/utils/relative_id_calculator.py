from amplihack.utils.logging_utils import log_call
class RelativeIdCalculator:
    @staticmethod
    @log_call
    def calculate(node_path: str) -> str:
        splitted = node_path.strip("/").split("/")
        if len(splitted) > 3:
            return "/" + "/".join(splitted[3:])
        return "/"
