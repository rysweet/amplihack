from typing import Any

from amplihack.vendor.blarify.repositories.graph_db_manager.db_manager import AbstractDbManager
from amplihack.vendor.blarify.repositories.graph_db_manager.queries import get_mermaid_graph
from amplihack.vendor.blarify.tools.utils import resolve_reference_id
from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, model_validator


class FlexibleInput(BaseModel):
    reference_id: str | None = Field(
        None, description="Reference ID (32-char handle) for the symbol"
    )
    file_path: str | None = Field(None, description="Path to the file containing the symbol")
    symbol_name: str | None = Field(None, description="Name of the function/class/method")
    depth: int = Field(
        default=2, description="Maximum depth of relationships to include (default: 2)", ge=1, le=5
    )

    @model_validator(mode="after")
    def validate_inputs(self):
        if self.reference_id:
            if len(self.reference_id) != 32:
                raise ValueError("Reference ID must be a 32 character string")
            return self
        if not (self.file_path and self.symbol_name):
            raise ValueError("Provide either reference_id OR (file_path AND symbol_name)")
        return self


class GetDependencyGraph(BaseTool):
    name: str = "get_dependency_graph"
    description: str = (
        "Generate a Mermaid diagram showing dependencies and relationships. "
        "Visualizes how symbols connect with configurable depth."
    )

    db_manager: AbstractDbManager = Field(description="Database manager for queries")

    args_schema: type[BaseModel] = FlexibleInput  # type: ignore[assignment]

    def __init__(self, db_manager: Any, handle_validation_error: bool = False):
        super().__init__(
            db_manager=db_manager,
            handle_validation_error=handle_validation_error,
        )

    def _run(
        self,
        reference_id: str | None = None,
        file_path: str | None = None,
        symbol_name: str | None = None,
        depth: int = 2,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        """Generate a Mermaid dependency graph for the specified symbol."""
        try:
            # Resolve the reference ID from inputs
            node_id = resolve_reference_id(
                self.db_manager,
                reference_id=reference_id,
                file_path=file_path,
                symbol_name=symbol_name,
            )

            # TODO: Pass depth parameter to get_mermaid_graph when it supports it
            return get_mermaid_graph(self.db_manager, node_id)
        except ValueError as e:
            return str(e)
