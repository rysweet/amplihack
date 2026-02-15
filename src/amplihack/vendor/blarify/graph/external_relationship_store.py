from typing import Any

from amplihack.vendor.blarify.graph.relationship.external_relationship import ExternalRelationship
from amplihack.vendor.blarify.graph.relationship.relationship_type import RelationshipType


class ExternalRelationshipStore:
    relationships: list[ExternalRelationship]

    def __init__(self) -> None:
        self.relationships: list[ExternalRelationship] = []

    def add_relationship(self, relationship: ExternalRelationship) -> None:
        self.relationships.append(relationship)

    def create_and_add_relationship(
        self, start_node_id: str, end_node_id: str, rel_type: RelationshipType
    ) -> None:
        relationship: ExternalRelationship = ExternalRelationship(
            start_node_id, end_node_id, rel_type
        )
        self.add_relationship(relationship)

    def get_relationships_as_objects(self) -> list[dict[str, Any]]:
        return [relationship.as_object() for relationship in self.relationships]
