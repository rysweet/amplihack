from typing import Any

from amplihack.vendor.blarify.graph.graph_environment import GraphEnvironment
from amplihack.vendor.blarify.graph.node.types.integration_node import IntegrationNode


class CommitNode(IntegrationNode):
    """Represents a commit node in the graph."""

    def __init__(
        self,
        external_id: str,
        title: str,
        diff_text: str,
        timestamp: str,
        author: str,
        url: str,
        metadata: dict[str, Any],
        graph_environment: GraphEnvironment,
    ):
        super().__init__(
            source="github",
            source_type="commit",
            external_id=external_id,
            title=title,
            content=diff_text,
            timestamp=timestamp,
            author=author,
            url=url,
            metadata=metadata,
            graph_environment=graph_environment,
        )
