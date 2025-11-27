import re
from typing import List

from tree_sitter import Node

from source_atlas.models.domain_models import RestEndpoint


class QuarkusJaxRsConfig:
    """Configuration for Quarkus JAX-RS annotations."""
    
    JAX_RS_HTTP_METHODS = {
        '@GET': 'GET',
        '@POST': 'POST',
        '@PUT': 'PUT',
        '@DELETE': 'DELETE',
        '@PATCH': 'PATCH',
        '@HEAD': 'HEAD',
        '@OPTIONS': 'OPTIONS',
    }


class QuarkusJaxRsExtractor:
    """Extracts REST endpoints from Quarkus JAX-RS annotations."""
    
    def supports(self, text: str) -> bool:
        """Check if the annotation is a JAX-RS HTTP method annotation."""
        return any(anno in text for anno in QuarkusJaxRsConfig.JAX_RS_HTTP_METHODS.keys())
    
    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        """
        Extract JAX-RS endpoint information.
        
        Args:
            text: The annotation text
            class_node: The class AST node
            method_node: The method AST node
            content: The file content
            
        Returns:
            List of extracted RestEndpoint objects
        """
        # Determine HTTP method type
        http_method = None
        for anno, method in QuarkusJaxRsConfig.JAX_RS_HTTP_METHODS.items():
            if anno in text:
                http_method = method
                break
        
        if not http_method:
            return []
        
        # Extract method-level @Path
        method_path = self._extract_path_from_method(method_node, content)
        
        # Extract class-level @Path
        class_path = self._extract_path_from_class(class_node, content)
        
        # Merge paths
        full_path = self._merge_paths(class_path, method_path)
        
        return [RestEndpoint(type=http_method, path=full_path)]
    
    def _extract_path_from_method(self, method_node: Node, content: str) -> str:
        """Extract @Path annotation from method."""
        if not method_node:
            return ""
        
        for child in method_node.children:
            if child.type != 'modifiers':
                continue
            
            for grandchild in child.children:
                if grandchild.type not in ('annotation', 'marker_annotation'):
                    continue
                
                annotation_text = content[grandchild.start_byte:grandchild.end_byte]
                if '@Path' in annotation_text:
                    return self._extract_path_value(annotation_text)
        
        return ""
    
    def _extract_path_from_class(self, class_node: Node, content: str) -> str:
        """Extract @Path annotation from class."""
        if not class_node:
            return ""
        
        for child in class_node.children:
            if child.type != 'modifiers':
                continue
            
            for grandchild in child.children:
                if grandchild.type not in ('annotation', 'marker_annotation'):
                    continue
                
                annotation_text = content[grandchild.start_byte:grandchild.end_byte]
                if '@Path' in annotation_text:
                    return self._extract_path_value(annotation_text)
        
        return ""
    
    def _extract_path_value(self, annotation_text: str) -> str:
        """
        Extract path value from @Path annotation.
        
        Handles formats like:
        - @Path("/users")
        - @Path(value = "/users")
        - @Path("/users/{id}")
        """
        # Try value = "..." format
        match = re.search(r'value\s*=\s*["\']([^"\']*)["\']', annotation_text)
        if match:
            return match.group(1)
        
        # Try simple @Path("...") format
        match = re.search(r'@Path\s*\(\s*["\']([^"\']*)["\']', annotation_text)
        if match:
            return match.group(1)
        
        return ""
    
    def _merge_paths(self, class_path: str, method_path: str) -> str:
        """
        Merge class-level and method-level paths.
        
        Args:
            class_path: Path from class-level @Path
            method_path: Path from method-level @Path
            
        Returns:
            Merged path
        """
        if not class_path and not method_path:
            return ""
        
        if not class_path:
            return method_path
        
        if not method_path:
            return class_path
        
        # Ensure proper path joining
        class_path = class_path.rstrip("/")
        method_path = method_path.lstrip("/")
        
        return f"{class_path}/{method_path}"
