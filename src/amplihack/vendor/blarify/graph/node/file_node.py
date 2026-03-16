from typing import Any

from .types.node_labels import NodeLabels

from .types.definition_node import DefinitionNode
from amplihack.utils.logging_utils import log_call


class FileNode(DefinitionNode):
    @log_call
    def __init__(self, **kwargs) -> None:
        super().__init__(label=NodeLabels.FILE, **kwargs)

    @property
    @log_call
    def node_repr_for_identifier(self) -> str:
        return "/" + self.name

    @log_call
    def as_object(self) -> dict[str, Any]:
        obj = super().as_object()
        obj["attributes"]["text"] = self.code_text
        return obj
