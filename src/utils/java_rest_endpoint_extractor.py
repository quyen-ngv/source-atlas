import re
from typing import Optional
from tree_sitter import Node
from models.domain_models import RestEndpoint
from models.analyzer_config import AnalyzerConfig

class JavaRestEndpointExtractor:
    """Extracts REST endpoint information from Java methods based on configurable annotations."""
    
    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.rest_annotations = config.rest_annotations or {
            '@GetMapping': 'GET',
            '@PostMapping': 'POST',
            '@PutMapping': 'PUT',
            '@DeleteMapping': 'DELETE',
            '@PatchMapping': 'PATCH',
            '@RequestMapping': 'REQUEST'
        }
    
    def extract_from_method(self, method_node: Node, content: str, class_node: Node = None) -> Optional[RestEndpoint]:
        """Extract REST endpoint info from method and class annotations."""
        
        method_path = ""
        http_method = None
        
        for child in method_node.children:
            if child.type == 'modifiers':
                for grandchild in child.children:
                    if grandchild.type == 'annotation':
                        text = content[grandchild.start_byte:grandchild.end_byte]
                        for anno, method in self.rest_annotations.items():
                            if anno in text:
                                path_match = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', text)
                                if path_match:
                                    method_path = path_match.group(1)
                                else:
                                    simple_path = re.search(r'@\w+\s*\(\s*["\']([^"\']*)["\']', text)
                                    if simple_path:
                                        method_path = simple_path.group(1)
                                
                                http_method = method
                                if anno == '@RequestMapping':
                                    method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', text)
                                    if method_match:
                                        http_method = method_match.group(1)
                                break
        
        class_path = ""
        if class_node:
            for child in class_node.children:
                if child.type == 'modifiers':
                    for grandchild in child.children:
                        if grandchild.type == 'annotation':
                            text = content[grandchild.start_byte:grandchild.end_byte]
                            if '@RequestMapping' in text:
                                path_match = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', text)
                                if path_match:
                                    class_path = path_match.group(1)
        
        if http_method:
            if class_path and method_path:
                full_path = class_path.rstrip('/') + '/' + method_path.lstrip('/')
            elif class_path:
                full_path = class_path
            else:
                full_path = method_path or ""
            return RestEndpoint(http_method=http_method, path=full_path)
        
        return None