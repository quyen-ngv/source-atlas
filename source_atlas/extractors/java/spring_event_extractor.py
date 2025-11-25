import re

from typing import List

from source_atlas.models.domain_models import RestEndpoint
from tree_sitter import Node

class EventAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@EventListener" in text

    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        classes = []
        m = re.search(r'\bclasses\s*=\s*\{([^}]*)\}', text)
        if m:
            classes = [c.strip().replace(".class", "") for c in m.group(1).split(",")]
        else:
            m = re.search(r'\bclasses\s*=\s*([A-Za-z_][\w\.]*\.class)', text)
            if m:
                classes = [m.group(1).replace(".class", "")]
        if not classes:
            # fallback: guess from method param
            for ch in method_node.children:
                if ch.type == 'formal_parameters':
                    params_src = content[ch.start_byte:ch.end_byte]
                    m = re.search(r'\(\s*([A-Za-z_][\w\.]*)\s+\w+', params_src)
                    if m:
                        classes = [m.group(1).split('.')[-1]]
                        break
        return [RestEndpoint(type="SPRING_EVENT_CONSUMER", consumes=ev) for ev in classes]
