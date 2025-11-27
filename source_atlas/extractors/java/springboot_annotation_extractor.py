import re
from typing import List

from tree_sitter import Node

from source_atlas.models.domain_models import RestEndpoint


class SpringBootAnnotationConfig:
    SPRING_BOOT_REST_ANNOTATION = {
        '@GetMapping': 'GET',
        '@PostMapping': 'POST',
        '@PutMapping': 'PUT',
        '@DeleteMapping': 'DELETE',
        '@PatchMapping': 'PATCH',
        '@RequestMapping': 'REQUEST',
    }
    
    # Additional Spring endpoint patterns
    EXCEPTION_HANDLER = '@ExceptionHandler'
    RESPONSE_BODY = '@ResponseBody'
    CONTROLLER = '@Controller'
    REST_CONTROLLER = '@RestController'
    REST_CONTROLLER_ADVICE = '@RestControllerAdvice'


class SpringBootAnnotationExtractor:
    def supports(self, text: str) -> bool:
        """Check if annotation is a Spring REST endpoint annotation."""
        # Support standard REST mappings
        if any(anno in text for anno in SpringBootAnnotationConfig.SPRING_BOOT_REST_ANNOTATION.keys()):
            return True
        
        # Support @ExceptionHandler
        if SpringBootAnnotationConfig.EXCEPTION_HANDLER in text:
            return True
        
        return False

    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        """Extract Spring endpoint information."""
        # Handle @ExceptionHandler
        if SpringBootAnnotationConfig.EXCEPTION_HANDLER in text:
            return self._extract_exception_handler(text, class_node, method_node, content)
        
        # Handle standard REST mappings
        return self._extract_rest_mapping(text, class_node, method_node, content)
    
    def _extract_exception_handler(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        """Extract @ExceptionHandler endpoint information."""
        # Extract exception class names
        exception_match = re.search(r'@ExceptionHandler\s*\(\s*(?:\{([^}]+)\}|([A-Za-z_]\w+(?:\.class)?))', text)
        
        exception_info = ""
        if exception_match:
            # Handle array format {Exception1.class, Exception2.class}
            if exception_match.group(1):
                exceptions = re.findall(r'([A-Za-z_]\w+)\.class', exception_match.group(1))
                exception_info = f"[{', '.join(exceptions)}]"
            # Handle single exception
            elif exception_match.group(2):
                exception_name = exception_match.group(2).replace('.class', '')
                exception_info = exception_name
        
        # Check if class is @RestControllerAdvice or @ControllerAdvice
        class_type = "EXCEPTION_HANDLER"
        if class_node:
            class_annotations = self._get_class_annotations(class_node, content)
            if SpringBootAnnotationConfig.REST_CONTROLLER_ADVICE in class_annotations:
                class_type = "REST_EXCEPTION_HANDLER"
        
        return [RestEndpoint(type=class_type, path=exception_info)]
    
    def _extract_rest_mapping(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        """Extract standard REST mapping endpoint information."""
        method_path, type = "", None

        # --- method-level path ---
        for anno, method in SpringBootAnnotationConfig.SPRING_BOOT_REST_ANNOTATION.items():
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

        # Check if method has @ResponseBody (for @Controller + @ResponseBody pattern)
        has_response_body = self._check_method_has_response_body(method_node, content)
        is_rest_controller = self._check_class_is_rest_controller(class_node, content)
        
        # Add note if this is a reactive endpoint (heuristic: check for Mono/Flux in return type)
        endpoint_type = type
        if type and self._is_reactive_endpoint(method_node, content):
            endpoint_type = f"{type}_REACTIVE"

        if type and (is_rest_controller or has_response_body):
            return [RestEndpoint(type=endpoint_type, path=full_path)]
        
        return []
    
    def _get_class_annotations(self, class_node: Node, content: str) -> str:
        """Get all annotations from class as a single string."""
        annotations = []
        if class_node:
            for child in class_node.children:
                if child.type == 'modifiers':
                    for grandchild in child.children:
                        if grandchild.type in ('annotation', 'marker_annotation'):
                            annotations.append(content[grandchild.start_byte:grandchild.end_byte])
        return ' '.join(annotations)
    
    def _check_method_has_response_body(self, method_node: Node, content: str) -> bool:
        """Check if method has @ResponseBody annotation."""
        if not method_node:
            return False
        
        for child in method_node.children:
            if child.type == 'modifiers':
                for grandchild in child.children:
                    if grandchild.type in ('annotation', 'marker_annotation'):
                        annotation_text = content[grandchild.start_byte:grandchild.end_byte]
                        if SpringBootAnnotationConfig.RESPONSE_BODY in annotation_text:
                            return True
        return False
    
    def _check_class_is_rest_controller(self, class_node: Node, content: str) -> bool:
        """Check if class is annotated with @RestController."""
        if not class_node:
            return False
        
        for child in class_node.children:
            if child.type == 'modifiers':
                for grandchild in child.children:
                    if grandchild.type in ('annotation', 'marker_annotation'):
                        annotation_text = content[grandchild.start_byte:grandchild.end_byte]
                        if SpringBootAnnotationConfig.REST_CONTROLLER in annotation_text:
                            return True
        return False
    
    def _is_reactive_endpoint(self, method_node: Node, content: str) -> bool:
        """Check if method returns reactive types (Mono/Flux)."""
        if not method_node:
            return False
        
        # Look for return type in method declaration
        for child in method_node.children:
            if child.type in ('type_identifier', 'generic_type'):
                type_text = content[child.start_byte:child.end_byte]
                if 'Mono' in type_text or 'Flux' in type_text:
                    return True
        
        return False
