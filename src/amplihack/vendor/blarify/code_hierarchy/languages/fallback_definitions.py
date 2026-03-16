from .language_definitions import LanguageDefinitions
from amplihack.utils.logging_utils import log_call


class FallbackDefinitions(LanguageDefinitions):
    @log_call
    def __init__(self) -> None:
        super().__init__()
