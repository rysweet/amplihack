import logging
from dataclasses import dataclass
from amplihack.utils.logging_utils import log_call

logger = logging.getLogger(__name__)


@dataclass
class GraphEnvironment:
    environment: str
    diff_identifier: str
    root_path: str

    @log_call
    def __str__(self):
        return f"/{self.environment}/{self.diff_identifier}"


if __name__ == "__main__":
    logger.info(GraphEnvironment("dev", None))
