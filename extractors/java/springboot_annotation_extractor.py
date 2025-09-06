import re
from typing import List
from models.domain_models import RestEndpoint
from tree_sitter import Node


class SpringBootAnnotationExtractor:
    def __init__(self, rest_annotations: dict):
        self.rest_annotations = rest_annotations

    def supports(self, text: str) -> bool:
        return any(anno in text for anno in self.rest_annotations.keys())

    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        method_path, type = "", None

        # --- method-level path ---
        for anno, method in self.rest_annotations.items():
            if anno in text:
                path_match = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', text)
                if path_match:
                    method_path = path_match.group(1)
                else:
                    simple_path = re.search(r'@\w+\s*\(\s*["\']([^"\']*)["\']', text)
                    if simple_path:
                        method_path = simple_path.group(1)

                type = method
                if anno == '@RequestMapping':
                    method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', text)
                    if method_match:
                        type = method_match.group(1)
                break

        # --- class-level path prefix ---
        class_path = ""
        if class_node:
            for child in class_node.children:
                if child.type == 'modifiers':
                    for grandchild in child.children:
                        if grandchild.type == 'annotation':
                            t = content[grandchild.start_byte:grandchild.end_byte]
                            if '@RequestMapping' in t:
                                m = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', t)
                                if m:
                                    class_path = m.group(1)

        # --- merge paths ---
        full_path = ""
        if class_path and method_path:
            full_path = class_path.rstrip("/") + "/" + method_path.lstrip("/")
        elif class_path:
            full_path = class_path
        else:
            full_path = method_path

        if type:
            return [RestEndpoint(type=type, path=full_path)]
        return []
