"""
This module contains the exceptions raised by the Multilspy framework.
"""
from amplihack.utils.logging_utils import log_call


class MultilspyException(Exception):
    """
    Exceptions raised by the Multilspy framework.
    """

    @log_call
    def __init__(self, message: str):
        """
        Initializes the exception with the given message.
        """
        super().__init__(message)
