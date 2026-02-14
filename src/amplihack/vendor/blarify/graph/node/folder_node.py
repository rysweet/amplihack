from collections.abc import Sequence
from typing import TYPE_CHECKING, Optional, Union

from .types.node import Node
from .types.node_labels import NodeLabels
from amplihack.vendor.blarify.graph.node.file_node import FileNode

if TYPE_CHECKING:
    from ...graph.graph_environment import GraphEnvironment
    from ...graph.relationship import Relationship


class FolderNode(Node):
    path: str
    name: str
    level: int

    def __init__(
        self,
        path: str,
        name: str,
        level: int,
        parent: Optional["Node"] = None,
        graph_environment: Optional["GraphEnvironment"] = None,
        layer: str = "code",
    ) -> None:
        self._contains: list[FileNode | FolderNode] = []
        super().__init__(NodeLabels.FOLDER, path, name, level, parent, graph_environment, layer)

    @property
    def node_repr_for_identifier(self) -> str:
        return "/" + self.name

    def _remove_trailing_slash(self, path: str) -> str:
        if path.endswith("/"):
            return path[:-1]
        return path

    def relate_node_as_contain_relationship(self, node: Union[FileNode, "FolderNode"]) -> None:
        self._contains.append(node)

    def relate_nodes_as_contain_relationship(
        self, nodes: Sequence[Union[FileNode, "FolderNode"]]
    ) -> None:
        for node in nodes:
            self.relate_node_as_contain_relationship(node)

    def get_relationships(self) -> list["Relationship"]:
        from ...graph.relationship import RelationshipCreator

        relationships = []
        for node in self._contains:
            relationships.append(RelationshipCreator.create_contains_relationship(self, node))

        return relationships

    def filter_children_by_path(self, paths: list[str]):
        self._contains = [node for node in self._contains if node.path in paths]
