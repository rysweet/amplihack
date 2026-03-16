from dataclasses import dataclass

from amplihack.vendor.blarify.graph.external_relationship_store import ExternalRelationshipStore
from amplihack.vendor.blarify.graph.graph import Graph
from amplihack.utils.logging_utils import log_call


@dataclass
class GraphUpdate:
    graph: Graph
    external_relationship_store: ExternalRelationshipStore

    @log_call
    def get_nodes_as_objects(self) -> list[dict]:
        return self.graph.get_nodes_as_objects()

    @log_call
    def get_relationships_as_objects(self) -> list[dict]:
        return (
            self.graph.get_relationships_as_objects()
            + self.external_relationship_store.get_relationships_as_objects()
        )
