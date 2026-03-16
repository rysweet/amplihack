import logging
from amplihack.utils.logging_utils import log_call

logger = logging.getLogger(__name__)


class Logger:
    @staticmethod
    @log_call
    def log(message: str) -> None:
        # if os.getenv("DEBUG"):
        logger.info(message)
