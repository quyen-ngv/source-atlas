import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

from tree_sitter import Language, Parser, Node, Query, QueryCursor

from models.domain_models import CodeChunk, Method, MethodCall, MethodParam
from models.analyzer_config import AnalyzerConfig
from processors.base_processor import BaseFileProcessor, ClassParsingContext
from processors.java.endpoint_extractor import JavaRestEndpointExtractor
from utils.comment_remover import JavaCommentRemover
from utils.tree_sitter_helper import extract_content

logger = logging.getLogger(__name__)

class JavaParsingConstants:
    CLASS_NODE_TYPES = {
        'class_declaration', 'interface_declaration',
        'enum_declaration', 'record_declaration',
        'annotation_type_declaration'
    }

    ENCODING_FALLBACKS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

@dataclass
class MethodDependencies:
    method_calls: List[str]
    variable_usage: List[str]
    field_access: List[str]

class JavaFileProcessor(BaseFileProcessor):
    def __init__(self, config: AnalyzerConfig, language: Language, parser: Parser,
                 lsp_service=None, project_root: str = None):
        super().__init__(config, language, parser)
        self.comment_remover = JavaCommentRemover()
        self.endpoint_extractor = JavaRestEndpointExtractor(config)
        self.lsp_service = lsp_service
        self.project_root = Path(project_root).resolve() if project_root else None

    def _extract_package(self, root_node: Node, content: str) -> str:
        try:
            package_query = Query(self.language, """
                (package_declaration
                    (scoped_identifier) @package)
            """)
            query_cursor = QueryCursor(package_query)
            captures = query_cursor.captures(root_node)
            package_nodes = captures.get("package")
            if package_nodes:
                return extract_content(package_nodes[0], content)
        except Exception as e:
            logger.debug(f"Error extracting package: {e}")
        return ""

    def _extract_all_class_nodes(self, root_node: Node) -> List[Node]:
        try:
            class_query = Query(self.language, """
                (class_declaration) @class
                (interface_declaration) @interface
                (enum_declaration) @enum
                (record_declaration) @record
                (annotation_type_declaration) @annotation
            """)
            query_cursor = QueryCursor(class_query)
            captures = query_cursor.captures(root_node)
            return [node for nodes in captures.values() for node in nodes]
        except Exception as e:
            logger.debug(f"Error extracting class nodes: {e}")
            return []

    def _extract_class_name(self, class_node: Node, content: str) -> Optional[str]:
        try:
            for child in class_node.children:
                if child.type == 'identifier':
                    return extract_content(child, content)
        except Exception:
            pass
        return None

    def _extract_method_name(self, class_node: Node, content: str) -> Optional[str]:
        method_name = None
        method_params = None
        try:
            for child in class_node.children:
                if child.type == 'identifier':
                    method_name = extract_content(child, content)
                if child.type == 'formal_parameters':
                    method_params = extract_content(child, content)
        except Exception:
            pass
        if method_name:
            return f"{method_name}{method_params}"
        else:
            return None

    def _is_nested_class(self, class_node: Node, root_node: Node) -> bool:
        parent = class_node.parent
        while parent and parent != root_node:
            if parent.type in JavaParsingConstants.CLASS_NODE_TYPES:
                return True
            parent = parent.parent
        return False

    def _build_full_class_name(self, class_name: str, package: str, class_node: Node,
                               content: str, root_node: Node) -> str:
        parent_names = []
        parent = class_node.parent

        while parent and parent != root_node:
            if parent.type in JavaParsingConstants.CLASS_NODE_TYPES:
                parent_name = self._extract_class_name(parent, content)
                if parent_name:
                    parent_names.append(parent_name)
            parent = parent.parent

        if parent_names:
            parent_names.reverse()
            nested_path = '.'.join(parent_names + [class_name])
            return f"{package}.{nested_path}" if package else nested_path

        return f"{package}.{class_name}" if package else class_name

    def _get_parent_class(self, class_node: Node, content: str, package: str) -> Optional[str]:
        parent = class_node.parent
        while parent:
            if parent.type in JavaParsingConstants.CLASS_NODE_TYPES:
                parent_name = self._extract_class_name(parent, content)
                if parent_name:
                    return self._build_full_class_name(parent_name, package, parent, content, parent)
            parent = parent.parent
        return None


    def _get_class_body(self, class_node: Node) -> Optional[Node]:
        for child in class_node.children:
            if child.type == 'class_body' or child.type == 'interface_body':
                return child
        return None

    def _extract_implements_with_lsp(self, class_node: Node, file_path: str) -> Tuple[str, ...]:
        interfaces = []
        try:
            implements_query = Query(self.language, """
                (class_declaration
                    interfaces: (super_interfaces
                        (type_list
                            (type_identifier) @interface)))
                (class_declaration
                    interfaces: (super_interfaces
                        (type_list
                            (generic_type
                                (type_identifier) @generic_interface))))
            """)

            query_cursor = QueryCursor(implements_query)
            captures = query_cursor.captures(class_node)
            for nodes in captures.values():
                for node in nodes:
                    resolved_interface = self._resolve_type_with_lsp(node, file_path)
                    if resolved_interface:
                        interfaces.append(resolved_interface)
        except Exception as e:
            logger.debug(f"Error extracting implements: {e}")
        return tuple(interfaces)

    def _extract_extends_with_lsp(self, class_node: Node, file_path: str) -> Optional[str]:
        try:
            extends_query = Query(self.language, """
                (class_declaration
                    superclass: (superclass
                        (type_identifier) @superclass))
                (class_declaration
                    superclass: (superclass
                        (generic_type
                            (type_identifier) @generic_superclass)))
            """)
            query_cursor = QueryCursor(extends_query)
            captures = query_cursor.captures(class_node)
            if captures:
                superclass_node = captures.values()[0]
                return self._resolve_type_with_lsp(superclass_node, file_path)
        except Exception as e:
            logger.debug(f"Error extracting extends: {e}")
        return None

    def _resolve_type_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self.lsp_service:
            return node.text.decode('utf8')

        try:
            line = node.start_point[0]
            col = node.start_point[1]
            lsp_results = self.lsp_service.request_definition(file_path, line, col)
            return self._process_lsp_results(lsp_results)

        except Exception as e:
            logger.debug(f"LSP resolution failed: {e}")
            return node.text.decode('utf8')

    def _process_lsp_results(self, lsp_results) -> Optional[str]:
        if not lsp_results:
            return None

        # Normalize to list
        results = lsp_results if isinstance(lsp_results, list) else [lsp_results]

        for result in results:
            if isinstance(result, dict):
                absolute_path = result.get('absolutePath')
                if absolute_path and isinstance(absolute_path, str):
                    if self._is_project_file(absolute_path):
                        qualified_name = self._extract_qualified_name_from_lsp_result(result)
                        if qualified_name:
                            return qualified_name
        return None

    # Method Processing
    def _extract_class_methods(self, class_node: Node, content: str,
                               implements: List[str], extends: Optional[str],
                               full_class_name: str, file_path: str) -> List[Method]:
        methods = []
        class_body = self._get_class_body(class_node)
        if not class_body:
            return methods

        try:
            for child in class_body.children:
                if child.type == 'method_declaration' or child.type == 'constructor_declaration':
                    method = self._process_method_node(
                        child, content, implements, extends,
                        full_class_name, class_node, file_path
                    )
                    if method:
                        methods.append(method)
        except Exception as e:
            logger.debug(f"Error extracting class methods: {e}")
        return methods

    def _process_method_node(self, method_node: Node, content: str,
                             implements: List[str], extends: Optional[str], full_class_name: str,
                             class_node: Node, file_path: str) -> Optional[Method]:
        try:
            method_name = self._extract_method_name(method_node, content)
            if not method_name:
                return None

            body, dependencies = self._extract_method_body_and_dependencies(method_node, content, file_path)
            endpoint = self.endpoint_extractor.extract_from_method(method_node, content, class_node)
            logger.info(f"endpoint {endpoint}")

            # Build inheritance info
            inheritance_info = self._build_inheritance_info(method_name, implements, extends)
            extends_info = self._build_extends_info(method_name, extends)

            return Method(
                name=f"{full_class_name}.{method_name}",
                body=body,
                method_calls=tuple(dependencies.method_calls),
                variable_usage=tuple(dependencies.variable_usage),
                field_access=tuple(dependencies.field_access),
                inheritance_info=tuple(inheritance_info),
                extends_info=tuple(extends_info),
                endpoint=endpoint
            )
        except Exception as e:
            logger.debug(f"Error processing method node: {e}")
            return None

    def _extract_method_body_and_dependencies(self, method_node: Node, content: str, file_path: str) -> Tuple[str, MethodDependencies]:
        body = ""
        dependencies = MethodDependencies([], [], [])

        for child in method_node.children:
            if child.type == 'block' or child.type == 'constructor_body':
                body = extract_content(method_node, content)
                dependencies = self._analyze_method_dependencies(child, file_path)
                break

        return body, dependencies

    def _analyze_method_dependencies(self, body_node: Node, file_path: str) -> MethodDependencies:
        method_calls = self._extract_method_calls(body_node, file_path)
        variable_usage = self._extract_variable_usage(body_node, file_path)
        field_access = self._extract_field_access(body_node, file_path)
        return MethodDependencies(method_calls, variable_usage, field_access)

    def _extract_method_calls(self, body_node: Node, file_path: str) -> List[MethodCall]:
        method_calls: List[MethodCall] = []
        try:
            method_call_query = Query(self.language, """
                (method_invocation 
                    name: (identifier) @method_call
                    arguments: (argument_list)
                )
            """)
            query_cursor = QueryCursor(method_call_query)
            captures = query_cursor.captures(body_node)
            for name, nodes in captures.items():
                if name == "method_call":
                    for node in nodes:
                        method_call = self._resolve_method_call_with_lsp(node, file_path)
                        if method_call:
                            method_calls.append(method_call)

        except Exception as e:
            logger.debug(f"Error extracting method calls: {e}")
        return list(method_calls)

    def _extract_field_access(self, body_node: Node, file_path: str) -> List[str]:
        field_access = set()
        try:
            field_access_query = Query(self.language, """
                (field_access field: (_) @field_name)
            """)
            query_cursor = QueryCursor(field_access_query)
            captures = query_cursor.captures(body_node)
            for capture_name, nodes in captures.items():
                if capture_name == "field_name":
                    for node in nodes:
                        resolved = self._resolve_field_access_with_lsp(node, file_path)
                        if resolved:
                            field_access.add(resolved)
        except Exception as e:
            logger.debug(f"Error extracting field access: {e}")
        return list(field_access)


    def _extract_variable_usage(self, body_node: Node, file_path: str) -> List[str]:
        variable_usage = set()
        try:
            variable_query = Query(self.language, """
                (local_variable_declaration type: (_) @var_type)
                (method_declaration type: (_) @return_type)
                (formal_parameter type: (_) @param_type)
                (spread_parameter (type_identifier) @varargs_type)
                (type_arguments (_) @generic_type)
                (array_type element: (_) @array_element_type)
            """)
            query_cursor = QueryCursor(variable_query)
            captures = query_cursor.captures(body_node)
            for capture_name, nodes in captures.items():
                if capture_name in {
                    "var_type", "return_type", "param_type", "varargs_type",
                    "generic_type", "array_element_type"
                }:  
                    for node in nodes:
                        variable_ref = self._resolve_variable_with_lsp(node, file_path)
                        if variable_ref:
                            variable_usage.add(variable_ref)
        except Exception as e:
            logger.debug(f"Error extracting variable usage: {e}")
        return list(variable_usage)

    def _resolve_method_call_with_lsp(self, node: Node, file_path: str) -> Optional[MethodCall]:
        if not self.lsp_service:
            return None

        try:
            line = node.start_point[0]
            col = node.start_point[1]
            # relative_file_path = self._get_relative_path_for_lsp(file_path)

            lsp_result = self.lsp_service.request_hover(file_path, line, col)

            return self._extract_method_from_hover(lsp_result)

        except Exception as e:
            logger.debug(f"LSP method call resolution failed: {e}")
            return None

    def _resolve_variable_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self.lsp_service:
            return None

        try:
            line = node.start_point[0]
            col = node.start_point[1]
            # relative_file_path = self._get_relative_path_for_lsp(file_path)

            lsp_results = self.lsp_service.request_definition(file_path, line, col)
            return self._process_lsp_results(lsp_results)

        except Exception as e:
            logger.debug(f"LSP variable resolution failed: {e}")
            return None

    def _resolve_field_access_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self.lsp_service:
            return None
        
        try:
            line = node.start_point[0]
            col = node.start_point[1]
            # relative_file_path = self._get_relative_path_for_lsp(file_path)
            
            lsp_results = self.lsp_service.request_hover(file_path, line, col)
            return self._extract_field_from_hover(lsp_results)

        except Exception as e:
            logger.debug(f"LSP field access resolution failed: {e}")
            return None

    def _extract_field_from_hover(self, lsp_result) -> Optional[str]:
        if not lsp_result or "contents" not in lsp_result:
            return None

        contents = lsp_result["contents"]
        if isinstance(contents, dict):
            field = contents.get("value")
        elif isinstance(contents, list) and contents:
            if isinstance(contents[0], dict):
                field = contents[0].get("value")
            else:
                field = str(contents[0])
        elif isinstance(contents, str):
            field = contents
        else:
            return None
            
        return field

    def _extract_method_from_hover(self, lsp_result) -> Optional[MethodCall]:
        if not lsp_result or "contents" not in lsp_result:
            return None

        contents = lsp_result["contents"]
        if isinstance(contents, dict):
            method = contents.get("value")
        elif isinstance(contents, list) and contents:
            if isinstance(contents[0], dict):
                method = contents[0].get("value")
            else:
                method = str(contents[0])
        elif isinstance(contents, str):
            method = contents
        else:
            return None

        if not method:
            return None

        # Ví dụ hover trả về:
        # "public String findById(String id = \"default\", int size = 10)"
        sig_pattern = r"([\w<>.\[\]]+\s+)?([\w.]+)\.([a-zA-Z_]\w*)\(([^)]*)\)"
        match = re.search(sig_pattern, method.strip())
        if not match:
            return None

        class_name = match.group(2)        # com.edu.repository.QuizRepository
        method_name = match.group(3)       # findById
        param_str = match.group(4).strip() # String id = "default", int size = 10

        params: List[MethodParam] = []
        if param_str:
            for p in param_str.split(","):
                p = p.strip()
                # parse "String id = \"default\""
                m = re.match(r"([\w<>.\[\]]+)\s+(\w+)(?:\s*=\s*(.+))?", p)
                if m:
                    param_type = m.group(1)
                    default_val = m.group(3).strip() if m.group(3) else None
                    params.append(MethodParam(type=param_type, value=default_val))
                else:
                    # fallback khi không match
                    params.append(MethodParam(type=p, value=None))

        return MethodCall(
            name=f"{class_name}.{method_name}",
            params=params
        )


    # Inheritance Analysis
    def _build_inheritance_info(self, method_name: str, implements: List[str], extends: Optional[str]) -> List[str]:
        inheritance_sources = []

        if extends:
            inheritance_sources.append(f"{extends}.{method_name}")

        if method_name:
            for interface in implements:
                    interface = self._remove_prefix(interface)
                    inheritance_sources.append(f"{interface}.{method_name}")

        return inheritance_sources

    def _remove_prefix(self, path: str) -> str:
        prefix = "src.main.java."
        if path.startswith(prefix):
            path = path[len(prefix):]
        return path

    def _build_extends_info(self, method_name: str, extends: Optional[str]) -> List[str]:
        """Build extends information for method"""
        if not extends or method_name not in {'equals', 'hashCode', 'toString'}:
            return []
        return [f"{extends}.{method_name}"]

    # Utility Methods
    def _get_relative_path_for_lsp(self, absolute_path: str) -> str:
        if not self.project_root:
            return absolute_path

        try:
            path = Path(absolute_path).resolve()
            project_root = self.project_root
            
            # Ensure both paths are absolute
            if not path.is_absolute():
                path = path.resolve()
            
            try:
                relative_path = path.relative_to(project_root)
                # Convert to forward slashes for consistency
                return str(relative_path).replace('\\', '/')
            except ValueError:
                # If the path is not relative to project root, return the original
                logger.debug(f"Path {path} is not relative to project root {project_root}")
                return absolute_path
        except Exception as e:
            logger.debug(f"Error getting relative path for LSP: {e}")
            return absolute_path

    def _is_project_file(self, absolute_path: str) -> bool:
        # logger.info(f"project_root {str(self.project_root)}")
        # logger.info(f"absolute_path {absolute_path}")
        # abs_norm = os.path.normpath(absolute_path)
        # file_norm = os.path.normpath(str(self.project_root))
        # common = os.path.commonpath([abs_norm, file_norm])
        # return (common != os.path.dirname(file_norm) and
        #         common != os.path.dirname(abs_norm) and
        #         len(common) > 0)
        return True

    def _extract_qualified_name_from_lsp_result(self, lsp_result: dict) -> str:
        try:
            absolute_path = lsp_result.get('absolutePath')
            if not absolute_path:
                logger.debug("No absolutePath found in LSP result")
                return ""
            
            # Ensure absolute_path is a string
            if not isinstance(absolute_path, str):
                logger.debug(f"absolutePath is not a string: {type(absolute_path)}")
                return ""
                
            return self._strip_root(absolute_path)
        except Exception as e:
            logger.debug(f"Failed to extract qualified name from LSP result: {e}")
            return ""

    def _strip_root(self, absolute_path: str) -> str:
        try:
            if not absolute_path or not isinstance(absolute_path, str):
                logger.debug(f"Invalid absolute_path: {absolute_path}")
                return ""
                
            abs_path = Path(absolute_path).resolve()
            root = Path(self.project_root).resolve()

            try:
                relative = abs_path.relative_to(root)
            except ValueError:
                logger.debug(f"abs path {abs_path}")
                return str(abs_path)

            result = str(relative).replace("\\", ".").replace("/", ".")
            if result.endswith(".java"):
                result = result[:-5]

            result = self._remove_prefix(result)
            return result
        except Exception as e:
            logger.debug(f"Error in _strip_root: {e}")
            return ""

    def _extract_qualified_name_from_external_path(self, absolute_path: str, class_name: str) -> str:
        try:
            path_str = str(absolute_path).replace('\\', '/')

            # Handle JDK/standard library classes
            for java_path in ['/java/', '/javax/']:
                idx = path_str.find(java_path)
                if idx != -1:
                    package_path = path_str[idx + 1:].replace('/', '.')
                    if package_path.endswith('.java'):
                        package_path = package_path[:-5]
                    return package_path

            # Try to extract from src/main/java structure
            path_parts = path_str.split('/')
            for i, part in enumerate(path_parts):
                if part in ['src', 'main', 'java'] and i + 1 < len(path_parts):
                    remaining_parts = path_parts[i + 1:]
                    package_path = '.'.join(remaining_parts)
                    if package_path.endswith('.java'):
                        package_path = package_path[:-5]
                    return package_path

            return class_name
        except Exception as e:
            logger.debug(f"Failed to extract qualified name from external path {absolute_path}: {e}")
            return class_name