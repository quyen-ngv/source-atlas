from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional

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

    def to_dict(self):
        return {
            "name": self.name,
            "params": self.params
        }

class ChunkType(Enum):
    REGULAR = "regular"
    GETTER = "getter"
    SETTER = "setter"
    CONSTRUCTOR = "constructor"
    STATIC = "static"
    ENDPOINT = "rest_endpoint"
    OVERRIDE = "override"
    CONFIGURATION = "configuration"

@dataclass
class Method:
    name: str
    body: str
    ast_hash: str
    method_calls: Tuple[MethodCall, ...]
    used_types: Tuple[str, ...]
    field_access: Tuple[str, ...]
    inheritance_info: Tuple[str, ...]
    endpoint: Tuple[RestEndpoint,...]
    type: ChunkType
    project_id: str
    branch: str
    handles_annotation: Optional[str] = None
    annotations: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self):
        return {
            "name": self.name,
            "body": self.body,
            "ast_hash": self.ast_hash,
            "method_calls": self.method_calls,
            "used_types": self.used_types,
            "field_access": self.field_access,
            "inheritance_fino": self.inheritance_info,
            "endpoint": self.endpoint,
            "type": self.type,
            "project_id": self.project_id,
            "branch": self.branch,
            "handles_annotation": self.handles_annotation,
            "annotations": list(self.annotations)
        }

@dataclass
class CodeChunk:
    package: Optional[str]
    class_name: Optional[str]
    full_class_name: Optional[str]
    file_path: str
    content: str
    ast_hash: str
    implements: Tuple[str, ...]
    methods: List[Method]
    parent_class: Optional[str]
    project_id: str
    branch: str
    used_types: Tuple[str,...]
    is_nested: bool = False
    type: ChunkType = ChunkType.REGULAR
    is_annotation: bool = False
    handles_annotation: Optional[str] = None
    annotations: Tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> Dict:
        """Convert CodeChunk to a JSON-serializable dictionary."""
        return {
            "package": self.package,
            "class_name": self.class_name,
            "full_class_name": self.full_class_name,
            "file_path": self.file_path,
            "content": self.content,
            "ast_hash": self.ast_hash,
            "implements": list(self.implements),
            "methods": [{
                "name": method.name,
                "body": method.body,
                "ast_hash": method.ast_hash,
                "method_calls": [{"name": method_call.name,
                                  "params": method_call.params} for method_call in method.method_calls],
                "used_types": list(method.used_types),
                "field_access": list(method.field_access),
                "inheritance_info": list(method.inheritance_info),
                "endpoint": method.endpoint,
                "type": method.type,
                "project_id": self.project_id,
                "branch": self.branch
            } for method in self.methods],
            "is_nested": self.is_nested,
            "parent_class": self.parent_class,
            "type": self.type,
            "project_id": self.project_id,
            "branch": self.branch,
            "is_annotation": self.is_annotation,
            "handles_annotation": self.handles_annotation,
            "annotations": list(self.annotations)
        }

    @classmethod
    def from_config(cls, file_path: Path, project_id: str, branch: str) -> "CodeChunk":
        return cls(
            package=None,
            class_name=None,
            full_class_name=None,
            file_path=str(file_path),
            content=file_path.read_text(),
            ast_hash="",  # Will be computed later
            implements=(),
            methods=[],
            parent_class=None,
            type=ChunkType.CONFIGURATION,
            project_id=project_id,
            branch=branch
        )
