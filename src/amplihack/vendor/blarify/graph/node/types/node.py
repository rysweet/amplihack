import os
from hashlib import md5
from typing import TYPE_CHECKING, Any, Optional

from amplihack.vendor.blarify.utils.format_verifier import FormatVerifier
from amplihack.vendor.blarify.utils.relative_id_calculator import RelativeIdCalculator
from amplihack.utils.logging_utils import log_call

if TYPE_CHECKING:
    from ....graph.graph_environment import GraphEnvironment
    from ....graph.node import NodeLabels
    from ....graph.relationship import Relationship


class Node:
    label: "NodeLabels"
    path: str
    name: str
    level: int
    parent: Optional["Node"]
    graph_environment: Optional["GraphEnvironment"]
    layer: str

    @log_call
    def __init__(
        self,
        label: "NodeLabels",
        path: str,
        name: str,
        level: int,
        parent: Optional["Node"] = None,
        graph_environment: Optional["GraphEnvironment"] = None,
        layer: str = "code",
    ) -> None:
        self.label = label
        self.path = path
        self.name = name
        self.level = level
        self.parent = parent
        self.graph_environment = graph_environment
        self.layer = layer

        if not self.is_path_format_valid():
            raise ValueError(f"Path format is not valid: {self.path}")

    @log_call
    def is_path_format_valid(self) -> bool:
        return FormatVerifier.is_path_uri(self.path)

    @property
    @log_call
    def hashed_id(self) -> str:
        return md5(self.id.encode()).hexdigest()

    @property
    @log_call
    def relative_id(self) -> str:
        """
        Returns the id without the graph environment prefix or root folder name
        """
        return RelativeIdCalculator.calculate(self.id)

    @property
    @log_call
    def id(self) -> str:
        return str(self.graph_environment or "") + self._identifier()

    @property
    @log_call
    def node_repr_for_identifier(self) -> str:
        raise NotImplementedError

    @property
    @log_call
    def pure_path(self) -> str:
        return self.path.replace("file://", "")

    @property
    @log_call
    def extension(self) -> str:
        return os.path.splitext(self.pure_path)[1]

    @log_call
    def as_object(self) -> dict[str, Any]:
        return {
            "type": self.label.name,
            "extra_labels": [],
            "attributes": {
                "label": self.label.name,
                "path": self.path,
                "node_id": self.hashed_id,
                "node_path": self.id,
                "name": self.name,
                "level": self.level,
                "hashed_id": self.hashed_id,
                "diff_identifier": self.graph_environment.diff_identifier
                if self.graph_environment
                else "",
                "layer": self.layer,
            },
        }

    @log_call
    def get_relationships(self) -> list["Relationship"]:
        return []

    @log_call
    def filter_children_by_path(self, paths: list[str]) -> None:
        pass

    @log_call
    def _identifier(self) -> str:
        identifier: str = ""

        if self.parent:
            identifier += self.parent._identifier()
        identifier += self.node_repr_for_identifier

        return identifier

    @log_call
    def update_graph_environment(self, environment: "GraphEnvironment") -> None:
        self.graph_environment = environment

    @log_call
    def __str__(self) -> str:
        return self._identifier()
