from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Tuple, Optional, Set

@dataclass
class Field:
    name: str
    type: str
    full_type: str
    annotations: Tuple[str, ...]

@dataclass
class RestEndpoint:
    type: str = ""
    path: str = ""
    produces: str = ""
    consumes: str = ""

@dataclass
class MethodParam:
    type: str = ""
    value: str = None

@dataclass
class MethodCall:
    name: str = ""
    params: List[MethodParam] = field(default_factory=list)

@dataclass
class Method:
    name: str
    body: str
    method_calls: Tuple[MethodCall, ...]
    variable_usage: Tuple[str, ...]
    field_access: Tuple[str, ...]
    inheritance_info: Tuple[str, ...]
    extends_info: Tuple[str, ...]
    endpoint: Optional[RestEndpoint]

class MethodType(Enum):
    REGULAR = "regular"
    GETTER = "getter"
    SETTER = "setter"
    CONSTRUCTOR = "constructor"
    STATIC = "static"
    REST_ENDPOINT = "rest_endpoint"
    OVERRIDE = "override"

@dataclass
class CodeChunk:
    package: str
    class_name: str
    full_class_name: str
    file_path: str
    content: str
    implements: Tuple[str, ...]
    extends: Optional[str]
    methods: List[Method]
    is_nested: bool
    parent_class: Optional[str]

    def to_dict(self) -> Dict:
        """Convert CodeChunk to a JSON-serializable dictionary."""
        return {
            "package": self.package,
            "class_name": self.class_name,
            "full_class_name": self.full_class_name,
            "file_path": self.file_path,
            "content": self.content,
            "implements": list(self.implements),
            "extends": self.extends,
            "methods": [{
                "name": method.name,
                "body": method.body,
                "method_calls": list(method.method_calls),
                "variable_usage": list(method.variable_usage),
                "field_access": list(method.field_access),
                "inheritance_info": list(method.inheritance_info),
                "extends_info": list(method.extends_info),
                "endpoint": method.endpoint
            } for method in self.methods],
            "is_nested": self.is_nested,
            "parent_class": self.parent_class,
        }

@dataclass
class DependencyGraph:
    nodes: Dict[str, CodeChunk]  # Maps class names to CodeChunk objects
    edges: Set[Tuple[str, str, str]]  # (source, target, relationship)

    def __init__(self):
        self.nodes = {}
        self.edges = set()
    
    def add_node(self, class_name: str, chunk: CodeChunk) -> None:
        """Add a node to the graph."""
        self.nodes[class_name] = chunk
    
    def add_edge(self, source: str, target: str, relationship: str) -> None:
        """Add an edge to the graph."""
        self.edges.add((source, target, relationship))
    
    def to_dict(self) -> Dict:
        """Convert DependencyGraph to a JSON-serializable dictionary."""
        return {
            "nodes": {name: chunk.to_dict() for name, chunk in self.nodes.items()},
            "edges": [{"source": source, "target": target, "relationship": rel} 
                      for source, target, rel in self.edges]
        }