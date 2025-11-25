import hashlib
import re
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from loguru import logger
from tree_sitter import Language, Parser, Node, Query, QueryCursor
from tree_sitter_language_pack import get_language

from source_atlas.analyzers.base_analyzer import BaseCodeAnalyzer
from source_atlas.analyzers.java_constants import JavaBuiltinPackages, JavaParsingConstants, JavaCodeAnalyzerConstant
from source_atlas.extractors.java.java_extractor import JavaEndpointExtractor
from source_atlas.lsp.lsp_service import LSPService
from source_atlas.models.domain_models import Method, MethodCall, ChunkType
from source_atlas.utils.comment_remover import JavaCommentRemover
from source_atlas.utils.common import normalize_whitespace
from source_atlas.utils.tree_sitter_helper import extract_content


@dataclass
class MethodDependencies:
    method_calls: List[str]
    used_types: List[str]
    field_access: List[str]


class JavaCodeAnalyzer(BaseCodeAnalyzer, ABC):

    # ============================================================================
    # SECTION 1: INITIALIZATION & CONTEXT MANAGEMENT
    # ============================================================================

    def __init__(self, root_path: str = None, project_id: str = None, branch: str = None):
        # Tree-sitter setup
        language: Language = get_language("java")
        parser = Parser(language)
        super().__init__(language, parser, project_id, branch)

        # Services
        self.comment_remover = JavaCommentRemover()
        self.endpoint_extractor = JavaEndpointExtractor()
        self.lsp_service = LSPService.create(root_path)
        self.project_id = project_id
        self.branch = branch
        self._server_ctx = None
        self.project_root = Path(root_path).resolve() if root_path else None

    def __enter__(self):
        self._server_ctx = self.lsp_service.start_server()
        self._server_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._server_ctx:
            self._server_ctx.__exit__(exc_type, exc_val, exc_tb)

    # ============================================================================
    # SECTION 2: ABSTRACT METHOD IMPLEMENTATIONS (from BaseCodeAnalyzer)
    # ============================================================================

    def _get_builtin_packages(self) -> List[str]:
        """Return Java builtin packages to be filtered."""
        return list(JavaBuiltinPackages.ALL_BUILTIN_PACKAGES)

    def _remove_source_prefix(self, path: str) -> str:
        """Remove 'src.main.java.' prefix from path."""
        prefix = "src.main.java."
        if path.startswith(prefix):
            return path[len(prefix):]
        return path

    def _get_code_files(self, root: Path) -> List[Path]:
        return list(root.rglob(JavaCodeAnalyzerConstant.JAVA_EXTENSION))

    def _extract_package(self, root_node: Node, content: str) -> str:
        try:
            captures = self._query_captures("""
                (package_declaration
                    (scoped_identifier) @package)
            """, root_node)
            package_nodes = captures.get("package")
            if package_nodes:
                return extract_content(package_nodes[0], content)
        except Exception as e:
            logger.debug(f"Error extracting package: {e}")
        return ""

    def _extract_all_class_nodes(self, root_node: Node) -> List[Node]:
        captures = self._query_captures("""
            (class_declaration) @class
            (interface_declaration) @interface
            (enum_declaration) @enum
            (record_declaration) @record
            (annotation_type_declaration) @annotation
        """, root_node)
        if not captures:
            return []
        return [node for nodes in captures.values() for node in nodes]

    def _extract_class_name(self, class_node: Node, content: str) -> Optional[str]:
        try:
            identifier = self._find_child_by_type(class_node, 'identifier')
            if identifier:
                return extract_content(identifier, content)
        except Exception as ex:
            logger.info(f"error _extract_class_name {ex}")
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

    def _is_config_node(self, node: Node, content: str):
        """Check if node is a configuration node based on annotations or implements/extends"""
        if node.type not in JavaParsingConstants.CLASS_NODE_TYPES:
            return False

        return self._has_config_annotations(node, content) or self._has_config_interfaces(node, content)

    def _should_check_implements(self, class_node: Node, content: str) -> bool:
        # Check if it's an interface
        if class_node.type == 'interface_declaration':
            return True

        # Check if it's an abstract class
        modifiers = self._find_child_by_type(class_node, 'modifiers')
        if modifiers:
            text_modifiers = extract_content(modifiers, content)
            if 'abstract' in text_modifiers:
                return True

        return False

    def _extract_implements_with_lsp(self, class_node: Node, file_path: str, content: str) -> List[str]:
        if not self._check_lsp_service():
            return []

        try:
            class_name_node = self._find_child_by_type(class_node, 'identifier')
            if not class_name_node:
                return []

            line, col = self._get_node_position(class_name_node)
            lsp_results = self.lsp_service.request_implementation(file_path, line, col)
            return self._resolve_lsp_implements(lsp_results)
        except Exception as e:
            logger.debug(f"LSP resolution failed: {e}")
            return []

    def _extract_class_methods(self, class_node: Node, content: str,
                               implements: List[str],
                               full_class_name: str, file_path: str, import_mapping: Dict[str, str]) -> List[Method]:
        methods = []
        class_body = self._get_class_body(class_node)
        if not class_body:
            return methods

        try:
            for child in class_body.children:
                if child.type == 'method_declaration' or child.type == 'constructor_declaration':
                    method = self._process_method_node(
                        child, content, implements,
                        full_class_name, class_node, file_path, import_mapping
                    )
                    if method:
                        methods.append(method)
        except Exception as e:
            logger.debug(f"Error extracting class methods: {e}")
        return methods

    def build_import_mapping(self, class_node: Node, content: str) -> Dict[str, str]:
        import_mapping = {}

        try:
            captures = self._query_captures("""
               (import_declaration
                  [
                    (scoped_identifier) @import_path
                    (identifier) @import_path
                  ]
                ) @test
            """, class_node)

            import_nodes = captures.get("import_path", [])
            for import_node in import_nodes:
                import_path = extract_content(import_node, content)
                if import_path and '.' in import_path:
                    class_name = import_path.split('.')[-1]
                    if class_name == "*":
                        continue
                    import_mapping[class_name] = import_path

        except Exception as e:
            logger.debug(f"Error building import mapping: {e}")

        return import_mapping

    def extract_class_use_types(self, class_node, content, file_path) -> Tuple[str, ...]:
        used_types = set()
        try:
            captures = self._query_captures("""
                (field_declaration
                    type: (_
                            (type_arguments (_) @generic_type)?
                        ) @field_type
                    )
            """, class_node)

            for capture_name, nodes in captures.items():
                if capture_name in {"field_type", "generic_type"}:
                    for node in nodes:
                        type_text = extract_content(node, content)
                        if type_text in JavaBuiltinPackages.JAVA_PRIMITIVES:
                            continue
                        resolved_type = self._resolve_used_type_with_lsp(node, file_path, type_text)
                        if resolved_type:
                            used_types.add(resolved_type)

        except Exception as e:
            logger.debug(f"Error extracting class use types: {e}")

        return tuple(self.filter_builtin_items(list(used_types)))

    # ============================================================================
    # SECTION 3: ANNOTATION CHECKING
    # ============================================================================

    def _has_annotations(self, node: Node, content: str, annotation_set: set) -> bool:
        """Generic method to check if node has any annotations from a given set."""
        try:
            captures = self._query_captures("""
                (modifiers (annotation) @annotation)
                (modifiers (marker_annotation) @annotation)
            """, node)
            
            for nodes in captures.values():
                for annotation_node in nodes:
                    annotation_text = extract_content(annotation_node, content)
                    if any(anno in annotation_text for anno in annotation_set):
                        return True
            return False
        except Exception as e:
            logger.debug(f"Error checking annotations: {e}")
            return False

    def _has_config_annotations(self, node: Node, content: str) -> bool:
        """Check if node has configuration annotations."""
        return self._has_annotations(node, content, JavaParsingConstants.CONFIG_NODE_ANNOTATIONS)

    def _has_config_interfaces(self, node: Node, content: str) -> bool:
        """Check if node implements/extends configuration interfaces"""
        implemented_classes = self._extract_implements_extends(node, content)
        return any(class_name in JavaParsingConstants.CONFIG_INTERFACES_CLASSES for class_name in implemented_classes)

    def _is_lombok_generated_position(self, root_node: Node, target_line: int, content: str) -> bool:
        """Check if the target line contains Lombok annotations that generate methods."""
        try:
            lines = content.split('\n')
            if target_line < len(lines):
                line_content = lines[target_line].strip()
                return any(lombok_ann in line_content 
                          for lombok_ann in JavaParsingConstants.LOMBOK_METHOD_ANNOTATIONS)
        except Exception:
            pass
        return False

    # ============================================================================
    # SECTION 4: CLASS PARSING
    # ============================================================================

    def _extract_implements_extends(self, class_node: Node, content: str) -> List[str]:
        """Extract class names from implements and extends clauses using tree-sitter query"""
        try:
            captures = self._query_captures("""
                (superclass (type_identifier) @extends_class)
                (super_interfaces (type_list (_ (type_identifier) @implements_class)))
            """, class_node)

            classes = []
            for capture_name, nodes in captures.items():
                for node in nodes:
                    class_name = extract_content(node, content)
                    if class_name:
                        classes.append(class_name)

            return classes
        except Exception as e:
            logger.debug(f"Error extracting implements/extends: {e}")
            return []

    def _get_class_body(self, class_node: Node) -> Optional[Node]:
        for child in class_node.children:
            if child.type == 'class_body' or child.type == 'interface_body':
                return child
        return None

    # ============================================================================
    # SECTION 5: METHOD PARSING
    # ============================================================================

    def _extract_method_name(self, class_node: Node, content: str) -> Tuple[Optional[str], Optional[Node]]:
        if class_node.type != 'method_declaration':
            return None, None

        method_name = None
        method_params = None
        method_name_node = None

        for child in class_node.children:
            if child.type == 'identifier':
                method_name = normalize_whitespace(extract_content(child, content))
                method_name_node = child
            elif child.type == 'formal_parameters':
                method_params = extract_content(child, content)
            if method_name is not None and method_params is not None:
                break

        if method_name is None:
            return None, None

        method_signature = f"{method_name}{method_params or '()'}"
        method_signature = normalize_whitespace(method_signature)
        return method_signature, method_name_node

    def _extract_all_method_names_from_class(self, class_node: Node, content: str, full_class_name: str) -> List[str]:
        method_names = []
        class_body = self._get_class_body(class_node)
        if not class_body:
            return method_names

        try:
            for child in class_body.children:
                if child.type == 'method_declaration' or child.type == 'constructor_declaration':
                    method_name, _ = self._extract_method_name(child, content)
                    if method_name:
                        # Extract just the method name (without parameters)
                        method_name_only = method_name.split('(')[0]
                        method_names.append(method_name_only)
        except Exception as e:
            logger.debug(f"Error extracting method names from class: {e}")

        return method_names

    def _process_method_node(self, method_node: Node, content: str,
                             implements: List[str], full_class_name: str,
                             class_node: Node, file_path: str, import_mapping: Dict[str, str]) -> Optional[Method]:
        try:
            method_name, method_name_node = self._extract_method_name(method_node, content)
            if not method_name:
                return None

            body = ""
            method_calls = self.filter_builtin_items(
                self._extract_method_calls(full_class_name, method_node, file_path, import_mapping, content))
            used_types = self.filter_builtin_items(self._extract_used_types(method_node, file_path, content, import_mapping))
            field_access = self.filter_builtin_items(self._extract_field_access(method_node, file_path))

            for child in method_node.children:
                if child.type == 'block' or child.type == 'constructor_body':
                    body = extract_content(method_node, content)
                    break

            endpoint = self.endpoint_extractor.extract_from_method(method_node, content, class_node)

            # Lazy evaluation: only check inheritance for methods without body (abstract/interface methods)
            inheritance_info = []
            if implements and self._should_check_inheritance(method_node):
                inheritance_info = self._build_inheritance_info(method_node, method_name_node, file_path)

            is_configuration = self._is_config_node(method_node, content)

            method_type = ChunkType.REGULAR
            if endpoint:
                method_type = ChunkType.ENDPOINT
            elif is_configuration:
                method_type = ChunkType.CONFIGURATION

            # Compute AST hash for method body
            method_ast_hash = self.compute_ast_hash(body)

            return Method(
                name=f"{full_class_name}.{method_name}",
                body=body,
                ast_hash=method_ast_hash,
                method_calls=tuple(method_calls),
                used_types=tuple(used_types),
                field_access=tuple(field_access),
                inheritance_info=tuple(inheritance_info),
                endpoint=tuple(endpoint),
                type=method_type,
                project_id=self.project_id,
                branch=self.branch
            )
        except Exception as e:
            logger.debug(f"Error processing method node: {e}")
            return None

    def _should_check_inheritance(self, method_node: Node) -> bool:
        for child in method_node.children:
            if child.type == 'block' or child.type == 'constructor_body':
                return False
        return True

    def _build_inheritance_info(self, method_node: Node, method_name_node: Node, file_path: str) -> List[str]:
        line, col = self._get_node_position(method_name_node)
        lsp_results = self.lsp_service.request_implementation(file_path, line, col)
        return self._resolve_lsp_method_implements(lsp_results)

    # ============================================================================
    # SECTION 6: METHOD CALL ANALYSIS
    # ============================================================================

    def _extract_method_calls(
            self,
            full_class_name: str,
            method_node: Node,
            file_path: str,
            import_mapping: Dict[str, str],
            content: str
    ) -> List[MethodCall]:
        method_calls: List[MethodCall] = []
        try:
            captures = self._query_method_invocations(method_node)
            return self._process_method_call_captures(captures, file_path, content)

        except Exception as e:
            logger.debug(f"Error extracting method calls: {e}")

        return method_calls

    def _query_method_invocations(self, method_node):
        return self._query_captures("""
            [
              (method_invocation
                object: (_) @object
                name: (identifier) @method_name
                arguments: (argument_list)? @arguments
              ) @call
    
              (method_invocation
                name: (identifier) @method_name
                arguments: (argument_list)? @arguments
              ) @call
            ]
        """, method_node)

    def _process_method_call_captures(self, captures: dict, file_path: str, content: str) -> List[MethodCall]:
        method_calls = []
        call_nodes = captures.get("call", [])
        object_nodes = captures.get("object", [])
        method_nodes = captures.get("method_name", [])
        args_nodes = captures.get("arguments", [])

        for i, call_node in enumerate(call_nodes):
            method_call = self._process_single_method_call(i, object_nodes, method_nodes, args_nodes, file_path,
                                                           content)
            if method_call:
                method_calls.append(method_call)

        return method_calls

    def _process_single_method_call(self, index: int, object_nodes: list, method_nodes: list, args_nodes: list,
                                    file_path: str, content: str) -> Optional[MethodCall]:
        object_node = object_nodes[index] if index < len(object_nodes) else None
        object_name = extract_content(object_node, content) if object_node else None

        if object_name and object_name in JavaBuiltinPackages.JAVA_PRIMITIVES:
            return None
        name_node = method_nodes[index] if index < len(method_nodes) else None
        method_name = normalize_whitespace(extract_content(name_node, content))
        if method_name and method_name not in self.methods_cache:
            logger.info(f"Method {method_name} not in methods cache")
            return None
        try:
            args_node = args_nodes[index] if index < len(args_nodes) else None

            resolved = self._resolve_method_call(name_node, args_node, file_path, content)
            if resolved and object_name and hasattr(resolved, "object_name"):
                resolved.object_name = object_name

            return resolved
        except Exception:
            return None

    def _resolve_method_call(self, node, args, file_path: str, content):
        if not self._check_lsp_service():
            return None

        try:
            line, col = self._get_node_position(node)
            lsp_result = self.lsp_service.request_definition(file_path, line, col)
            if not lsp_result or len(lsp_result) == 0:
                return None

            full_method_def = self._build_method_definition(lsp_result[0])
            return MethodCall(name=full_method_def, params=[]) if full_method_def else None

        except Exception as e:
            logger.debug(f"LSP method call resolution failed: {e}")
            return None

    def _build_method_definition(self, result: dict) -> Optional[str]:
        raw_absolute_path = self._get_valid_absolute_path(result)
        if not raw_absolute_path:
            return None

        absolute_path = self._strip_root(raw_absolute_path)
        if not absolute_path:
            return None

        qualified_name = self._extract_method_with_params_from_lsp_result(result)
        if not qualified_name:
            return None

        if self._has_multiple_classes(raw_absolute_path):
            absolute_path = self._resolve_class_path_with_hover(result, raw_absolute_path)
            if not absolute_path:
                return None

        return f"{absolute_path}.{qualified_name}"

    # ============================================================================
    # SECTION 7: TYPE ANALYSIS
    # ============================================================================

    def _extract_used_types(self, body_node: Node, file_path: str, content: str, import_mapping: Dict[str, str]) -> \
            List[str]:
        used_types = set()
        try:
            variable_query = Query(self.language, """
                (local_variable_declaration type: (_) @var_type)
                (method_declaration type: (_) @return_type)
                (formal_parameter type: (_) @param_type)
                (spread_parameter (type_identifier) @varargs_type)
                (type_arguments (_) @generic_type)
                (array_type element: (_) @array_element_type)
                (scoped_type_identifier) @first_scoped
                (#not-ancestor? @first_scoped scoped_type_identifier)
            """)
            query_cursor = QueryCursor(variable_query)
            captures = query_cursor.captures(body_node)
            for capture_name, nodes in captures.items():
                if capture_name in {
                    "var_type", "return_type", "param_type", "varargs_type",
                    "generic_type", "array_element_type", "first_scoped"
                }:
                    for node in nodes:
                        text = extract_content(node, content)
                        if text in JavaBuiltinPackages.JAVA_PRIMITIVES:
                            continue
                        variable_ref = import_mapping.get(text, self._resolve_used_type_with_lsp(node, file_path, text))
                        if variable_ref:
                            used_types.add(variable_ref)
        except Exception as e:
            logger.debug(f"Error extracting variable usage: {e}")
        return list(used_types)

    def _extract_field_access(self, body_node: Node, file_path: str) -> List[str]:
        field_access = set()
        try:
            captures = self._query_captures("""
                (field_access field: (_) @field_name)
            """, body_node)
            
            for capture_name, nodes in captures.items():
                if capture_name == "field_name":
                    for node in nodes:
                        resolved = self._resolve_field_access_with_lsp(node, file_path)
                        if resolved:
                            field_access.add(resolved)
        except Exception as e:
            logger.debug(f"Error extracting field access: {e}")
        return list(field_access)

    def extract_local_variables(self, body_node: Node, file_path: str, content: str) -> Dict[str, str]:
        variables = {}

        try:
            captures = self._query_captures("""
                [
                  (local_variable_declaration
                    type: (_) @type
                    declarator: (variable_declarator
                      name: (identifier) @var_name
                    )
                  ) @declaration
                  
                  (formal_parameter
                    type: (_) @type
                    name: (identifier) @var_name
                  ) @param
                ]
            """, body_node)

            type_nodes = captures.get("type", [])
            var_nodes = captures.get("var_name", [])

            for i in range(min(len(type_nodes), len(var_nodes))):
                # Extract type text (handles List<String>, String[], etc.)
                type_text = extract_content(type_nodes[i], content)
                var_name = extract_content(var_nodes[i], content)
                variables[var_name] = type_text

        except Exception as e:
            logger.debug(f"Error extracting variables: {e}")

        return variables

    # ============================================================================
    # SECTION 8: LSP RESULT PROCESSING
    # ============================================================================

    # ---------- 8.1 Core LSP Processors ----------

    def _resolve_lsp_implements(self, lsp_results) -> List[str]:
        """Process LSP implementation results."""
        def processor(result):
            absolute_path = self._get_valid_absolute_path(result)
            if absolute_path:
                return self._extract_qualified_name_from_lsp_result(result)
            return None
        
        return self._normalize_and_process_lsp_results(lsp_results, processor)

    def _resolve_lsp_method_implements(self, lsp_results) -> List[str]:
        """Process LSP method implementation results."""
        def processor(result):
            absolute_path = self._get_valid_absolute_path(result)
            if absolute_path:
                class_path = self._extract_qualified_name_from_lsp_result(result)
                method_name = self._extract_method_with_params_from_lsp_result(result)
                if class_path and method_name:
                    return f"{class_path}.{method_name}"
            return None
        
        return self._normalize_and_process_lsp_results(lsp_results, processor)

    def _resolve_lsp_type_response(self, lsp_results, type_name: str = None) -> Optional[str]:
        if not lsp_results:
            return None

        # Normalize to list
        results = lsp_results if isinstance(lsp_results, list) else [lsp_results]

        for result in results:
            qualified_name = self._extract_qualified_name_from_result(result)
            if qualified_name:
                return self._adjust_qualified_name_for_type(qualified_name, type_name)
        return None

    # ---------- 8.2 LSP Extraction Helpers ----------

    def _extract_method_with_params_from_lsp_result(self, lsp_result: dict) -> str:
        """Extract method signature from LSP result."""
        try:
            file_info = self._extract_file_info_from_lsp(lsp_result)
            if not file_info:
                return None
            
            file_path, start_line, start_char = file_info
            method_node = self._find_method_from_file(file_path, start_line, start_char)
            
            if not method_node:
                return None
            
            # Extract method name and return
            content = self._read_file_content(file_path)
            if not content:
                return None
            method_name, _ = self._extract_method_name(method_node, content)
            return method_name
            
        except Exception as e:
            logger.debug(f"Error extracting method from lsp result: {e}")
            return None

    def _extract_file_info_from_lsp(self, lsp_result: dict) -> Optional[Tuple[str, int, int]]:
        """Extract file path and position from LSP result."""
        file_path = lsp_result.get('absolutePath') or lsp_result.get('uri', '').replace('file:///', '')
        if not file_path:
            logger.debug("No file path found in LSP result")
            return None

        range_info = lsp_result.get('range')
        if not range_info:
            logger.debug("No range info found in LSP result")
            return None

        start_line = range_info['start']['line']
        start_char = range_info['start']['character']
        
        return (file_path, start_line, start_char)

    def _find_method_from_file(self, file_path: str, line: int, character: int) -> Optional[Node]:
        """Parse file and find method node at specified position."""
        try:
            content = self._read_file_content(file_path)
            if not content:
                return None
                
            tree = self.parser.parse(content.encode('utf-8'))
            root_node = tree.root_node

            # Find the method node at the specified position
            method_node = self._find_method_at_position(root_node, line, character)
            
            if not method_node:
                # Check if this might be a Lombok-generated method
                if self._is_lombok_generated_position(root_node, line, content):
                    logger.debug(f"Skipping Lombok-generated method at line {line} in {file_path}")
                else:
                    logger.debug(f"No method found at line {line}, character {character} file {file_path}")
                return None
                
            return method_node
            
        except Exception as e:
            logger.debug(f"Error parsing file {file_path}: {e}")
            return None

    def _extract_qualified_name_from_result(self, result) -> Optional[str]:
        absolute_path = self._get_valid_absolute_path(result)
        if not absolute_path:
            return None
        return self._extract_method_with_params_from_lsp_result(result)

    def _adjust_qualified_name_for_type(self, qualified_name: str, type_name: str) -> str:
        if not (type_name and type_name != "var" and "." in qualified_name):
            return qualified_name

        class_type = qualified_name.split('.')[-1]
        if class_type == type_name:
            return qualified_name

        if "." in type_name:
            return qualified_name.rsplit(".", 1)[0] + "." + type_name
        else:
            return qualified_name.rstrip(".") + "." + type_name

    # ---------- 8.3 LSP Resolution with Specific Types ----------

    def _resolve_used_type_with_lsp(self, node: Node, file_path: str, type_name: str) -> Optional[str]:
        if not self._check_lsp_service():
            return None

        try:
            line, col = self._get_node_position(node)
            lsp_results = self.lsp_service.request_definition(file_path, line, col)
            return self._resolve_lsp_type_response(lsp_results, type_name)

        except Exception as e:
            logger.debug(f"LSP variable resolution failed: {e}")
            return None

    def _resolve_field_access_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self._check_lsp_service():
            return None

        try:
            line = node.end_point[0]
            col = node.end_point[1]

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

    def _resolve_class_path_with_hover(self, result: dict, file_path: str) -> Optional[str]:
        try:
            line = result.get('range', {}).get('start', {}).get('line')
            col = result.get('range', {}).get('start', {}).get('character')

            lsp_hover = self.lsp_service.request_hover(file_path, line, col)
            if not lsp_hover:
                return None

            method_value = lsp_hover.get('contents', {}).get('value')
            return self._resolve_class_from_hover(method_value)
        except Exception:
            return None

    def _resolve_class_from_hover(self, signature: str) -> str:
        pattern_with_class = re.compile(
            r"""^(?P<return>(?:@\w+(?:\([^)]*\))?\s+)*
        (?:[\w$.]+)
        (?:<[^>]+>+)?
        (?:\[\])*
    )\s+
    (?P<class>[\w$.]+)\.(?P<method>\w+)\(""",
            re.VERBOSE,
        )

        s = signature.strip()
        m = pattern_with_class.match(s)
        if not m:
            return None

        return m.groupdict().get('class')

    # ============================================================================
    # SECTION 9: TREE-SITTER UTILITIES
    # ============================================================================

    def _find_method_at_position(self, root_node: Node, target_line: int, target_char: int) -> Optional[Node]:
        """Find the method declaration node that contains the target position"""
        try:
            captures = self._query_captures("(method_declaration) @method", root_node)

            for method_node in captures.get('method', []):
                if self._is_position_in_method_identifier(method_node, target_line, target_char):
                    return method_node
            return None
        except Exception as e:
            logger.debug(f"Error finding method at position: {e}")
            return None

    def _is_position_in_method_identifier(self, method_node: Node, target_line: int, target_char: int) -> bool:
        for child in method_node.children:
            if child.type == 'identifier':
                return (child.start_point[0] == target_line and
                        child.start_point[1] <= target_char <= child.end_point[1])
        return False

    def _has_multiple_classes(self, file_path: str) -> bool:
        try:
            content = self._read_file_content(file_path)
            if not content:
                return False
            tree = self.parser.parse(content.encode('utf-8'))
            class_nodes = self._extract_all_class_nodes(tree.root_node)
            return len(class_nodes) > 1
        except Exception as e:
            logger.debug(f"Error checking multiple classes: {e}")
            return False

    # ============================================================================
    # SECTION 10: HELPER UTILITIES (Eliminate Code Duplication)
    # ============================================================================

    def _get_node_position(self, node: Node) -> Tuple[int, int]:
        """Extract line and column from node's start position."""
        return node.start_point[0], node.start_point[1]

    def _query_captures(self, query_string: str, node: Node) -> dict:
        """Execute tree-sitter query and return captures."""
        try:
            query = Query(self.language, query_string)
            return QueryCursor(query).captures(node)
        except Exception as e:
            logger.debug(f"Query execution failed: {e}")
            return {}

    def _find_child_by_type(self, node: Node, child_type: str) -> Optional[Node]:
        """Find first child node with specified type."""
        for child in node.children:
            if child.type == child_type:
                return child
        return None

    def _find_children_by_types(self, node: Node, child_types: set) -> List[Node]:
        """Find all children with types in the specified set."""
        return [child for child in node.children if child.type in child_types]

    def _validate_dict_result(self, result) -> bool:
        """Check if result is a valid dictionary."""
        return isinstance(result, dict)

    def _get_valid_absolute_path(self, result: dict) -> Optional[str]:
        """Extract and validate absolutePath from LSP result."""
        if not self._validate_dict_result(result):
            return None
        absolute_path = result.get('absolutePath')
        return absolute_path if (absolute_path and isinstance(absolute_path, str)) else None

    def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read file content with UTF-8 encoding and error handling."""
        try:
            return Path(file_path).read_text(encoding='utf-8')
        except Exception as e:
            logger.debug(f"Error reading file {file_path}: {e}")
            return None

    def _check_lsp_service(self) -> bool:
        """Check if LSP service is available."""
        return self.lsp_service is not None
