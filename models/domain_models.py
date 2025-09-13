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

class MethodType(Enum):
    REGULAR = "regular"
    GETTER = "getter"
    SETTER = "setter"
    CONSTRUCTOR = "constructor"
    STATIC = "static"
    REST_ENDPOINT = "rest_endpoint"
    OVERRIDE = "override"

@dataclass
class Method:
    name: str
    body: str
    method_calls: Tuple[MethodCall, ...]
    used_types: Tuple[str, ...]
    field_access: Tuple[str, ...]
    inheritance_info: Tuple[str, ...]
    extends_info: Tuple[str, ...]
    endpoint: Optional[RestEndpoint]
    type: MethodType

    def to_dict(self):
        return {
            "name": self.name,
            "body": self.body,
            "method_calls": self.method_calls,
            "used_types": self.used_types,
            "field_access": self.field_access,
            "inheritance_fino": self.inheritance_info,
            "extends_info": self.extends_info,
            "endpoint": self.endpoint,
            "type": self.type
        }

@dataclass
class CodeChunk:
    package: Optional[str]
    class_name: Optional[str]
    full_class_name: Optional[str]
    file_path: str
    content: str
    implements: Tuple[str, ...]
    extends: Optional[str]
    methods: List[Method]
    parent_class: Optional[str]
    is_nested: bool = False
    is_config_file: bool = False

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
                "method_calls": [{"name": method_call.name,
                                  "params": method_call.params} for method_call in method.method_calls],
                "used_types": list(method.used_types),
                "field_access": list(method.field_access),
                "inheritance_info": list(method.inheritance_info),
                "extends_info": list(method.extends_info),
                "endpoint": method.endpoint,
                "type": method.type
            } for method in self.methods],
            "is_nested": self.is_nested,
            "parent_class": self.parent_class,
        }

    @classmethod
    def from_config(cls, file_path: Path) -> "CodeChunk":
        return cls(
            package=None,
            class_name=None,
            full_class_name=None,
            file_path=str(file_path),
            content=file_path.read_text(),
            is_config_file=True,
            implements=(),
            extends=None,
            methods=[],
            parent_class=None
        )
