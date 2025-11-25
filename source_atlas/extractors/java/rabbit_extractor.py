import re

from typing import List

from source_atlas.models.domain_models import RestEndpoint
from tree_sitter import Node

class RabbitAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@RabbitListener" in text

    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        queues = []
        m = re.search(r'\bqueues\s*=\s*\{([^}]*)\}', text)
        if m:
            queues = [q.strip().strip('"\'') for q in m.group(1).split(",")]
        m = re.search(r'\bqueues\s*=\s*("([^"]+)"|\'([^\']+)\')', text)
        if m:
            queues.append(m.group(2) or m.group(3))
        return [RestEndpoint(type="RABBIT_CONSUMER", consumes=q) for q in queues]