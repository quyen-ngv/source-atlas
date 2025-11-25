from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Neo4jNodeDto(BaseModel):
    id: Optional[int] = None
    labels: List[str] = []
    properties: Dict[str, Any] = {}

    project_id: Optional[str] = None
    branch: Optional[str] = None
    pull_request_id: Optional[str] = None

    class_name: Optional[str] = None
    method_name: Optional[str] = None
    file_path: Optional[str] = None
    content: Optional[str] = None
    ast_hash: Optional[str] = None

    endpoint: Optional[str] = None

    class Config:
        extra = "allow"

    def to_str(self):
        return f"""
            class_name: {self.class_name},
            method_name: {self.method_name},
            project_id: {self.project_id},
            branch: {self.branch},
            content: {self.content},
            endpoint: {self.endpoint},
        """


class Neo4jRelationshipDto(BaseModel):
    id: Optional[int] = None
    type: str
    start_node: Neo4jNodeDto
    end_node: Neo4jNodeDto
    properties: Dict[str, Any] = {}


class Neo4jPathDto(BaseModel):
    start_node: Neo4jNodeDto
    end_node: Neo4jNodeDto
    total_length: int
    nodes: List[Neo4jNodeDto]
    relationships: List[Neo4jRelationshipDto]
    path_summary: List[Dict[str, Any]] = []


class Neo4jTraversalResultDto(BaseModel):
    endpoint: Neo4jNodeDto
    paths: List[Neo4jPathDto]
    visited_nodes: List[Neo4jNodeDto]