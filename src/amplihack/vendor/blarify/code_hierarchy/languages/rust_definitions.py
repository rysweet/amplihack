import tree_sitter_rust as tsrust
from amplihack.vendor.blarify.code_hierarchy.languages.FoundRelationshipScope import FoundRelationshipScope
from amplihack.vendor.blarify.graph.node import Node as GraphNode
from amplihack.vendor.blarify.graph.node import NodeLabels
from amplihack.vendor.blarify.graph.relationship import RelationshipType
from tree_sitter import Language, Node, Parser

from .language_definitions import LanguageDefinitions


class RustDefinitions(LanguageDefinitions):
    CONTROL_FLOW_STATEMENTS = []
    CONSEQUENCE_STATEMENTS = []

    def get_language_name() -> str:
        return "rust"

    def get_parsers_for_extensions() -> dict[str, Parser]:
        return {
            ".rs": Parser(Language(tsrust.language())),
        }

    def should_create_node(node: Node) -> bool:
        return LanguageDefinitions._should_create_node_base_implementation(
            node,
            [
                "function_item",
                "impl_item",
                "struct_item",
                "enum_item",
                "trait_item",
                "mod_item",
                "type_item",
            ],
        )

    def get_identifier_node(node: Node) -> Node:
        # impl_item has no "name" field; use the "type" field instead
        # e.g. `impl Foo { ... }` -> type field is "Foo"
        # e.g. `impl Trait for Foo { ... }` -> type field is "Trait"
        if node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            if type_node is not None:
                return type_node
        return LanguageDefinitions._get_identifier_node_base_implementation(node)

    def get_body_node(node: Node) -> Node:
        return LanguageDefinitions._get_body_node_base_implementation(node)

    def get_relationship_type(
        node: GraphNode, node_in_point_reference: Node
    ) -> FoundRelationshipScope | None:
        return RustDefinitions._find_relationship_type(
            node_label=node.label,
            node_in_point_reference=node_in_point_reference,
        )

    def get_node_label_from_type(type: str) -> NodeLabels:
        return {
            "function_item": NodeLabels.FUNCTION,
            "impl_item": NodeLabels.CLASS,
            "struct_item": NodeLabels.CLASS,
            "enum_item": NodeLabels.CLASS,
            "trait_item": NodeLabels.CLASS,
            "mod_item": NodeLabels.CLASS,
            "type_item": NodeLabels.CLASS,
        }[type]

    def get_language_file_extensions() -> set[str]:
        return {".rs"}

    def _find_relationship_type(
        node_label: str, node_in_point_reference: Node
    ) -> FoundRelationshipScope | None:
        relationship_types = RustDefinitions._get_relationship_types_by_label()
        relevant_relationship_types = relationship_types.get(node_label, {})

        return LanguageDefinitions._traverse_and_find_relationships(
            node_in_point_reference, relevant_relationship_types
        )

    def _get_relationship_types_by_label() -> dict[str, RelationshipType]:
        return {
            NodeLabels.CLASS: {
                "use_declaration": RelationshipType.IMPORTS,
                "field_declaration": RelationshipType.TYPES,
                "struct_expression": RelationshipType.INSTANTIATES,
            },
            NodeLabels.FUNCTION: {
                "use_declaration": RelationshipType.IMPORTS,
                "call_expression": RelationshipType.CALLS,
            },
        }
