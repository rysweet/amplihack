from typing import Any

from amplihack.vendor.blarify.repositories.graph_db_manager.dtos.node_search_result_dto import (
    EdgeDTO,
    ReferenceSearchResultDTO,
)


class Neo4jNodeSearchResultAdapter:
    """Adapter to convert Neo4j query results to NodeSearchResultDTO."""

    @staticmethod
    def adapt(
        node_data: tuple[dict[str, Any], list[Any], list[dict[str, Any]]]
        | tuple[dict[str, Any], list[Any], list[dict[str, Any]], list[dict[str, Any]]],
    ) -> ReferenceSearchResultDTO:
        """
        Adapt Neo4j query results to NodeSearchResultDTO.

        Args:
            node_data: Tuple of (node_info, outbound_relations, inbound_relations, workflows)

        Returns:
            NodeSearchResultDTO: Adapted data transfer object
        """

        # Handle both 3-tuple (legacy) and 4-tuple (with workflows) formats
        if len(node_data) == 3:
            node_info, outbound_relations, inbound_relations = node_data
            workflows = []
        else:
            node_info, outbound_relations, inbound_relations, workflows = node_data

        # Convert relationship data to EdgeDTO objects
        inbound_edges = []
        if inbound_relations:
            for rel in inbound_relations:
                if rel.get("node_id"):  # Filter out null relationships
                    inbound_edges.append(
                        EdgeDTO(
                            node_id=rel.get("node_id", ""),
                            node_name=rel.get("node_name", ""),
                            node_type=rel.get("node_type", []),
                            relationship_type=rel.get("relationship_type", ""),
                        )
                    )

        outbound_edges = []
        if outbound_relations:
            for rel in outbound_relations:
                if rel.get("node_id"):  # Filter out null relationships
                    outbound_edges.append(
                        EdgeDTO(
                            node_id=rel.get("node_id", ""),
                            node_name=rel.get("node_name", ""),
                            node_type=rel.get("node_type", []),
                            relationship_type=rel.get("relationship_type", ""),
                        )
                    )

        return ReferenceSearchResultDTO(
            node_id=node_info.get("node_id", ""),
            node_name=node_info.get("node_name", ""),
            node_labels=node_info.get("labels", []),
            node_path=node_info.get("node_path", ""),
            code=node_info.get("text") or "",
            start_line=node_info.get("start_line"),
            end_line=node_info.get("end_line"),
            file_path=node_info.get("file_path"),
            inbound_relations=inbound_edges if inbound_edges else None,
            outbound_relations=outbound_edges if outbound_edges else None,
            documentation=node_info.get("documentation"),
            workflows=workflows if workflows else None,
        )
