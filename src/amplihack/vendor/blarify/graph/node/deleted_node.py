from .types.node import Node
from amplihack.vendor.blarify.utils.path_calculator import PathCalculator
from amplihack.utils.logging_utils import log_call


class DeletedNode(Node):
    @log_call
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @log_call
    def _identifier(self):
        return PathCalculator.compute_relative_path_with_prefix(
            self.pure_path, self.graph_environment.root_path
        )
