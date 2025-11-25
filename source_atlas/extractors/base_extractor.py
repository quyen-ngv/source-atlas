from typing import List, Protocol
from tree_sitter import Node
from source_atlas.models.domain_models import RestEndpoint

class AnnotationDependencyExtractor(Protocol):
    def supports(self, annotation_text: str) -> bool: ...
    def extract(self, annotation_text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]: ...
