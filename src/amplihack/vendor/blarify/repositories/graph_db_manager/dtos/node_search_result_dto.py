"""NodeSearchResultDTO for representing node search results."""

from typing import Any

from pydantic import BaseModel, ConfigDict

from .edge_dto import EdgeDTO


class ReferenceSearchResultDTO(BaseModel):
    """Data Transfer Object for node search results."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    node_name: str
    node_labels: list[str]
    node_path: str
    code: str
    start_line: int | None = None
    end_line: int | None = None
    file_path: str | None = None
    # Enhanced fields for relationships
    inbound_relations: list[EdgeDTO] | None = None
    outbound_relations: list[EdgeDTO] | None = None
    # Documentation nodes that describe this code node
    documentation: str | None = None
    # Workflows that this node belongs to
    workflows: list[dict[str, Any]] | None = None
