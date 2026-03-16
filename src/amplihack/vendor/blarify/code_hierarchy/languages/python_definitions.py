import tree_sitter_python as tspython
from amplihack.vendor.blarify.code_hierarchy.languages.FoundRelationshipScope import FoundRelationshipScope
from amplihack.vendor.blarify.graph.node import Node as GraphNode
from amplihack.vendor.blarify.graph.node import NodeLabels
from amplihack.vendor.blarify.graph.relationship import RelationshipType
from tree_sitter import Language, Node, Parser

from .language_definitions import LanguageDefinitions
from amplihack.utils.logging_utils import log_call


class PythonDefinitions(LanguageDefinitions):
    CONTROL_FLOW_STATEMENTS = ["if_statement", "while_statement", "for_statement"]
    CONSEQUENCE_STATEMENTS = ["block"]

    @log_call
    def get_language_name() -> str:
        return "python"

    @log_call
    def get_parsers_for_extensions() -> dict[str, Parser]:
        return {
            ".py": Parser(Language(tspython.language())),
        }

    @log_call
    def should_create_node(node: Node) -> bool:
        return LanguageDefinitions._should_create_node_base_implementation(
            node, ["class_definition", "function_definition"]
        )

    @log_call
    def get_identifier_node(node: Node) -> Node:
        return LanguageDefinitions._get_identifier_node_base_implementation(node)

    @log_call
    def get_body_node(node: Node) -> Node:
        return LanguageDefinitions._get_body_node_base_implementation(node)

    @log_call
    def get_relationship_type(
        node: GraphNode, node_in_point_reference: Node
    ) -> FoundRelationshipScope | None:
        return PythonDefinitions._find_relationship_type(
            node_label=node.label,
            node_in_point_reference=node_in_point_reference,
        )

    @log_call
    def get_node_label_from_type(type: str) -> NodeLabels:
        return {
            "class_definition": NodeLabels.CLASS,
            "function_definition": NodeLabels.FUNCTION,
        }[type]

    @log_call
    def get_language_file_extensions() -> set[str]:
        return {".py"}

    @log_call
    def _find_relationship_type(
        node_label: str, node_in_point_reference: Node
    ) -> FoundRelationshipScope | None:
        relationship_types = PythonDefinitions._get_relationship_types_by_label()
        relevant_relationship_types = relationship_types.get(node_label, {})

        return LanguageDefinitions._traverse_and_find_relationships(
            node_in_point_reference, relevant_relationship_types
        )

    @log_call
    def _get_relationship_types_by_label() -> dict[str, RelationshipType]:
        return {
            NodeLabels.CLASS: {
                "import_from_statement": RelationshipType.IMPORTS,
                "superclasses": RelationshipType.INHERITS,
                "call": RelationshipType.INSTANTIATES,
                "typing": RelationshipType.TYPES,
                "assignment": RelationshipType.TYPES,
            },
            NodeLabels.FUNCTION: {
                "call": RelationshipType.CALLS,
                "interpolation": RelationshipType.CALLS,
                "import_from_statement": RelationshipType.IMPORTS,
                "assignment": RelationshipType.ASSIGNS,
            },
        }
