from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from amplihack.vendor.blarify.graph.node import Node, NodeLabels
from amplihack.vendor.blarify.graph.node.file_node import FileNode
from amplihack.vendor.blarify.graph.node.folder_node import FolderNode

if TYPE_CHECKING:
    from ..graph.relationship import Relationship


class Graph:
    nodes_by_path: defaultdict[str, set[Node]]
    file_nodes_by_path: dict[str, FileNode]
    folder_nodes_by_path: dict[str, FolderNode]
    nodes_by_label: defaultdict[str, set[Node]]
    nodes_by_relative_id: dict[str, Node]
    __nodes: dict[str, Node]
    __references_relationships: list["Relationship"]

    def __init__(self) -> None:
        self.__nodes: dict[str, Node] = {}
        self.__references_relationships: list[Relationship] = []
        self.nodes_by_path: defaultdict[str, set[Node]] = defaultdict(set)
        self.file_nodes_by_path: dict[str, FileNode] = {}
        self.folder_nodes_by_path: dict[str, FolderNode] = {}
        self.nodes_by_label: defaultdict[str, set[Node]] = defaultdict(set)
        self.nodes_by_relative_id: dict[str, Node] = {}

    def has_folder_node_with_path(self, path: str) -> bool:
        return path in self.folder_nodes_by_path

    def add_nodes(self, nodes: Sequence[Node]) -> None:
        for node in nodes:
            self.add_node(node)

    def add_node(self, node: Node) -> None:
        self.__nodes[node.id] = node
        self.nodes_by_path[node.path].add(node)
        self.nodes_by_label[node.label.value].add(node)
        self.nodes_by_relative_id[node.relative_id] = node

        if node.label == NodeLabels.FILE:
            self.file_nodes_by_path[node.path] = cast(FileNode, node)

        if node.label == NodeLabels.FOLDER:
            self.folder_nodes_by_path[node.path] = cast(FolderNode, node)

    def get_nodes_by_path(self, path: str) -> set[Node]:
        return self.nodes_by_path[path]

    def get_file_node_by_path(self, path: str) -> Node | None:
        return self.file_nodes_by_path.get(path)

    def get_folder_node_by_path(self, path: str) -> FolderNode:
        return self.folder_nodes_by_path[path]

    def get_nodes_by_label(self, label: str) -> set[Node]:
        return self.nodes_by_label[label]

    def get_node_by_id(self, id: str) -> Node | None:
        return self.__nodes.get(id)

    def get_node_by_relative_id(self, relative_id: str) -> Node | None:
        return self.nodes_by_relative_id.get(relative_id)

    def get_relationships_as_objects(self) -> list[dict[str, Any]]:
        internal_relationships = [
            relationship.as_object() for relationship in self.get_relationships_from_nodes()
        ]
        reference_relationships = [
            relationship.as_object() for relationship in self.__references_relationships
        ]

        return internal_relationships + reference_relationships

    def get_relationships_from_nodes(self) -> list["Relationship"]:
        relationships: list[Relationship] = []
        for node in self.__nodes.values():
            relationships.extend(node.get_relationships())

        return relationships

    def add_references_relationships(self, references_relationships: list["Relationship"]) -> None:
        self.__references_relationships.extend(references_relationships)

    def get_nodes_as_objects(self) -> list[dict[str, Any]]:
        return [node.as_object() for node in self.__nodes.values()]

    def filtered_graph_by_paths(self, paths_to_keep: list[str]) -> "Graph":
        graph: Graph = Graph()
        for node in self.__nodes.values():
            if node.path in paths_to_keep:
                node.filter_children_by_path(paths_to_keep)
                graph.add_node(node)

        for relationship in self.__references_relationships:
            if (
                relationship.start_node.path in paths_to_keep
                or relationship.end_node.path in paths_to_keep
            ):
                graph.add_references_relationships([relationship])

        return graph

    def __str__(self) -> str:
        to_return: str = ""

        for node in self.__nodes.values():
            to_return += f"{node}\n"

        for relationship in self.__references_relationships:
            to_return += f"{relationship}\n"

        return to_return
