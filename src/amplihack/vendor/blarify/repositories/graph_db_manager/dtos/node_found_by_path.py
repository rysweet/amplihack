from pydantic import BaseModel
from amplihack.utils.logging_utils import log_call


class NodeFoundByPathDto(BaseModel):
    node_id: str
    name: str
    label: str
    node_path: str

    @log_call
    def as_dict(self):
        return {
            "node_id": self.node_id,
            "name": self.name,
            "label": self.label,
            "node_path": self.node_path,
        }
