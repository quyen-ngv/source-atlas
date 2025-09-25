import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from tree_sitter import Language, Parser, Node, Query, QueryCursor
from tree_sitter_language_pack import get_language

from analyzers.base_analyzer import BaseCodeAnalyzer
from extractors.java.java_extractor import JavaEndpointExtractor
from lsp.implements.java_lsp import JavaLSPService
from models.domain_models import Method, MethodCall, MethodParam, ChunkType
from utils.comment_remover import JavaCommentRemover
from utils.tree_sitter_helper import extract_content

logger = logging.getLogger(__name__)

class JavaBuiltinPackages:
    # Core Java packages
    JAVA_CORE_PACKAGES = {
        'java.lang',
        'java.util',
        'java.io',
        'java.nio',
        'java.net',
        'java.time',
        'java.math',
        'java.text',
        'java.security',
        'java.sql',
        'java.beans',
        'java.awt',
        'java.swing',
        'java.applet',
        'java.rmi',
        'java.lang.reflect',
        'java.lang.annotation',
        'java.util.concurrent',
        'java.util.function',
        'java.util.stream',
        'java.util.regex',
        'java.nio.file',
        'java.nio.charset',
        'java.security.cert',
        'java.time.format',
        'java.time.temporal',
        'java.time.chrono',
        'java.time.zone'
    }

    # Java EE / Jakarta EE packages
    JAVA_EE_PACKAGES = {
        'javax.servlet',
        'javax.persistence',
        'javax.validation',
        'javax.annotation',
        'javax.inject',
        'javax.ejb',
        'javax.jms',
        'javax.mail',
        'javax.xml',
        'javax.ws.rs',
        'jakarta.servlet',
        'jakarta.persistence',
        'jakarta.validation',
        'jakarta.annotation',
        'jakarta.inject',
        'jakarta.ejb',
        'jakarta.jms',
        'jakarta.mail',
        'jakarta.xml',
        'jakarta.ws.rs'
    }

    # Spring Framework packages
    SPRING_PACKAGES = {
        'org.springframework',
        'org.springframework.boot',
        'org.springframework.context',
        'org.springframework.beans',
        'org.springframework.web',
        'org.springframework.data',
        'org.springframework.security',
        'org.springframework.transaction',
        'org.springframework.util',
        'org.springframework.core',
        'org.springframework.aop',
        'org.springframework.jdbc',
        'org.springframework.orm',
        'org.springframework.jms',
        'org.springframework.cache',
        'org.springframework.test'
    }

    # Common third-party library packages
    COMMON_LIBRARY_PACKAGES = {
        'org.slf4j',
        'org.apache.commons',
        'org.apache.logging',
        'com.fasterxml.jackson',
        'com.google.gson',
        'org.junit',
        'org.mockito',
        'org.hibernate',
        'com.mysql',
        'org.postgresql',
        'redis.clients',
        'com.mongodb',
        'org.apache.kafka',
        'org.apache.http',
        'okhttp3',
        'retrofit2'
    }

    # Tất cả packages cần exclude
    ALL_BUILTIN_PACKAGES = (
            JAVA_CORE_PACKAGES |
            JAVA_EE_PACKAGES |
            SPRING_PACKAGES |
            COMMON_LIBRARY_PACKAGES
    )

    # Primitive types và wrapper classes
    JAVA_PRIMITIVES = {
        # --- Primitive types ---
        "byte", "short", "int", "long",
        "float", "double", "char", "boolean", "void",

        # --- Wrapper classes (java.lang) ---
        "Boolean", "Byte", "Short", "Integer", "Long",
        "Float", "Double", "Character", "Void",

        # --- Core java.lang classes ---
        "Object", "Class", "Enum", "Record", "String",
        "StringBuilder", "StringBuffer",
        "Math", "System", "Thread", "Runnable",
        "Exception", "RuntimeException", "Error", "Throwable",
        "Comparable", "Iterable",

        # --- java.util common classes & interfaces ---
        "Collection", "List", "Set", "Map", "Queue", "Deque",
        "ArrayList", "LinkedList", "HashSet", "TreeSet",
        "HashMap", "TreeMap", "Hashtable", "Vector",
        "Collections", "Arrays", "Objects",
        "Optional", "Stream",

        # --- java.util.concurrent ---
        "CompletableFuture",

        # --- java.time (Java 8+) ---
        "LocalDate", "LocalTime", "LocalDateTime", "ZonedDateTime",
        "Instant", "Duration", "Period",
        "ZoneId", "ZoneOffset", "DateTimeFormatter",

        # --- java.math ---
        "BigDecimal", "BigInteger",

        # --- java.nio.file ---
        "Path", "Paths", "Files",

        # --- java.nio.charset ---
        "Charset", "StandardCharsets",

        # --- java.io (very common) ---
        "File", "InputStream", "OutputStream", "Reader", "Writer",

        # --- java.net (very common) ---
        "URL", "URI",

        # --- Miscellaneous ---
        "UUID"
    }

class JavaParsingConstants:
    CLASS_NODE_TYPES = {
        'class_declaration', 'interface_declaration',
        'enum_declaration', 'record_declaration',
        'annotation_type_declaration'
    }

    ENCODING_FALLBACKS = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

    CONFIG_NODE_ANNOTATIONS  = {
        # --- Class-level configuration ---
        "@Configuration",
        "@SpringBootApplication",
        "@EnableAutoConfiguration",
        "@EnableConfigurationProperties",
        "@ComponentScan",
        "@Import",
        "@ImportResource",

        # --- Method-level bean definitions ---
        "@Bean",

        # --- Web filters / advice / listeners ---
        "@WebFilter",
        "@WebListener",
        "@ControllerAdvice",
        "@RestControllerAdvice",

        "@Aspect",

        # --- Conditional configuration ---
        "@Profile",
        "@ConditionalOnClass",
        "@ConditionalOnMissingBean",
        "@ConditionalOnProperty",
        "@ConditionalOnExpression",
        "@ConditionalOnBean",
    }

@dataclass
class MethodDependencies:
    method_calls: List[str]
    used_types: List[str]
    field_access: List[str]

class JavaCodeAnalyzerConstant:
    JAVA_CONFIG_EXTENSIONS = {
        "*.sql", "*.yml", "*.yaml", "*.xml"
    }

    JAVA_EXTENSION = "*.java"


class JavaCodeAnalyzer(BaseCodeAnalyzer):

    def __init__(self, root_path: str = None, project_id: str = None, branch: str = None):
        # Tree-sitter setup
        language: Language = get_language("java")
        parser = Parser(language)
        super().__init__(language, parser, project_id, branch)

        # Services
        self.comment_remover = JavaCommentRemover()
        self.lsp_service = JavaLSPService.create(root_path)
        self.project_id = project_id
        self.branch = branch
        self._server_ctx = None
        self.comment_remover = JavaCommentRemover()
        self.endpoint_extractor = JavaEndpointExtractor()
        self.project_root = Path(root_path).resolve() if root_path else None
        self.builtin_packages = (
                JavaBuiltinPackages.JAVA_CORE_PACKAGES |
                JavaBuiltinPackages.JAVA_EE_PACKAGES |
                JavaBuiltinPackages.SPRING_PACKAGES |
                JavaBuiltinPackages.COMMON_LIBRARY_PACKAGES
        )
    def __enter__(self):
        self._server_ctx = self.lsp_service.start_server()
        self._server_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._server_ctx:
            self._server_ctx.__exit__(exc_type, exc_val, exc_tb)

    # ---- extension points ----
    def _get_code_files(self, root: Path) -> List[Path]:
        return list(root.rglob(JavaCodeAnalyzerConstant.JAVA_EXTENSION))

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
        except Exception as ex:
            logger.info(f"error _extract_class_name {ex}")
            pass
        return None

    def _extract_method_name(self, class_node: Node, content: str) -> Tuple[Optional[str], Optional[Node]]:
        if class_node.type != 'method_declaration':
            return None, None

        method_name = None
        method_params = None
        method_name_node = None

        for child in class_node.children:
            if child.type == 'identifier':
                method_name = extract_content(child, content)
                method_name_node = child
            elif child.type == 'formal_parameters':
                method_params = extract_content(child, content)
            if method_name is not None and method_params is not None:
                break

        if method_name is None:
            return None, None

        method_signature = f"{method_name}{method_params or '()'}"
        return method_signature, method_name_node

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

    def _extract_implements_with_lsp(self, class_node: Node, file_path: str, content: str) -> List[str, ...]:
        if not self.lsp_service:
            return []

        try:
            class_name_node = None
            is_interface = False
            if class_node.type == 'interface_declaration':
                is_interface = True
            for child in class_node.children:
                if not is_interface:
                    if child.type == 'modifiers':
                        text_modifiers = extract_content(child, content)
                        if ' abstract' not in text_modifiers:
                            return []
                if child.type == 'identifier':
                    class_name_node = child

            if not class_name_node:
                return []

            line = class_name_node.start_point[0]
            col = class_name_node.start_point[1]
            logger.info(f'request_implementation {file_path}, {line}, {col}')
            lsp_results = self.lsp_service.request_implementation(file_path, line, col)
            logger.info(f'request_implementation 1 done')
            return self._resolve_lsp_implements(lsp_results)
        except Exception as e:
            logger.debug(f"LSP resolution failed: {e}")
            return []

    def _resolve_type_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self.lsp_service:
            return node.text.decode('utf8')

        try:
            line = node.start_point[0]
            col = node.start_point[1]
            lsp_results = self.lsp_service.request_definition(file_path, line, col)
            return self._resolve_lsp_type_response(lsp_results)

        except Exception as e:
            logger.debug(f"LSP resolution failed: {e}")
            return node.text.decode('utf8')

    def _resolve_lsp_implements(self, lsp_results) -> List[str, ...]:
        if not lsp_results:
            return ()

        # Normalize to list
        results = lsp_results if isinstance(lsp_results, list) else [lsp_results]

        response = []
        for result in results:
            absolute_path = result.get('absolutePath')
            if absolute_path and isinstance(absolute_path, str):
                qualified_name = self._extract_qualified_name_from_lsp_result(result)
                logger.info(f"qualified_name {qualified_name}")
                response.append(qualified_name)
        return response

    def _resolve_lsp_method_implements(self, lsp_results) -> List[str]:
        if not lsp_results:
            return None

        # Normalize to list
        results = lsp_results if isinstance(lsp_results, list) else [lsp_results]

        response: List[str] = []
        for result in results:
            if isinstance(result, dict):
                absolute_path = result.get('absolutePath')
                if absolute_path and isinstance(absolute_path, str):
                    absolute_path = self._extract_qualified_name_from_lsp_result(result)
                    qualified_name = self.extract_method_with_params_from_lsp_result(result)
                    logger.info(f"qualified_name {absolute_path}.{qualified_name}")
                    response.append(f"{absolute_path}.{qualified_name}")
        return response

    def extract_method_with_params_from_lsp_result(self, lsp_result: dict) -> str:
        try:
            # Get file path and position info
            file_path = lsp_result.get('absolutePath') or lsp_result.get('uri', '').replace('file:///', '')
            if not file_path:
                logger.error("No file path found in LSP result")
                return None

            range_info = lsp_result.get('range')
            if not range_info:
                logger.error("No range info found in LSP result")
                return None

            start_line = range_info['start']['line']
            start_char = range_info['start']['character']

            content = Path(file_path).read_text(encoding='utf-8')

            # Parse the file
            tree = self.parser.parse(content.encode('utf-8'))
            root_node = tree.root_node

            # Find the method node at the specified position
            method_node = self._find_method_at_position(root_node, start_line, start_char)
            if not method_node:
                logger.error(f"No method found at line {start_line}, character {start_char}")
                return None

            # Extract method details
            method_name, method_name_nod = self._extract_method_name(method_node, content)
            return method_name

        except Exception as e:
            logger.error(f"Error extracting method from LSP result: {e}")
            return None

    def _find_method_at_position(self, root_node: Node, target_line: int, target_char: int) -> Optional[Node]:
        """Find the method declaration node that contains the target position"""

        def find_method_recursive(node: Node) -> Optional[Node]:
            # Check if this node is a method declaration
            if node.type == 'method_declaration':
                # Check if the target position is within this method's identifier
                for child in node.children:
                    if child.type == 'identifier':
                        start_line = child.start_point[0]
                        end_line = child.end_point[0]
                        start_char = child.start_point[1]
                        end_char = child.end_point[1]

                        if (start_line == target_line and
                                start_char <= target_char <= end_char):
                            return node

            # Recursively search children
            for child in node.children:
                result = find_method_recursive(child)
                if result:
                    return result

            return None

        return find_method_recursive(root_node)

    def _resolve_lsp_type_response(self, lsp_results, type_name: str = None) -> Optional[str]:
        if not lsp_results:
            return None

        # Normalize to list
        results = lsp_results if isinstance(lsp_results, list) else [lsp_results]

        for result in results:
            if isinstance(result, dict):
                absolute_path = result.get('absolutePath')
                if absolute_path and isinstance(absolute_path, str):
                    qualified_name = self._extract_qualified_name_from_lsp_result(result)
                    if type_name and type_name != "var" and "." in qualified_name:
                        class_type = qualified_name.split(".")[-1]
                        if class_type != type_name:
                            if "." in type_name:
                                qualified_name = qualified_name.rsplit(".", 1)[0] + "." + type_name
                            else:
                                qualified_name = qualified_name.rstrip(".") + "." + type_name
                    if qualified_name:
                        return qualified_name
        return None

    # Method Processing
    def _extract_class_methods(self, class_node: Node, content: str,
                               implements: List[str],
                               full_class_name: str,  file_path: str, import_mapping: Dict[str, str]) -> List[Method]:
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

    def _process_method_node(self, method_node: Node, content: str,
                             implements: List[str], full_class_name: str,
                             class_node: Node, file_path: str, import_mapping: Dict[str, str]) -> Optional[Method]:
        try:
            method_name, method_name_node = self._extract_method_name(method_node, content)
            if not method_name:
                return None

            body = ""
            method_calls = self.filter(self._extract_method_calls(full_class_name, method_node, file_path, import_mapping, content))
            used_types = self.filter(self._extract_used_types(method_node, file_path, content, import_mapping))
            field_access = self.filter(self._extract_field_access(method_node, file_path))

            for child in method_node.children:
                if child.type == 'block' or child.type == 'constructor_body':
                    # body = extract_content(method_node, content)
                    break

            endpoint = self.endpoint_extractor.extract_from_method(method_node, content, class_node)

            # Build inheritance info
            inheritance_info = self._build_inheritance_info(method_node, method_name_node, file_path) if implements else []
            is_configuration = self._is_config_node(method_node, content)

            method_type = ChunkType.REGULAR
            if endpoint:
                method_type = ChunkType.ENDPOINT
            elif is_configuration:
                method_type = ChunkType.CONFIGURATION

            return Method(
                name=f"{full_class_name}.{method_name}",
                body=body,
                method_calls=tuple(method_calls),
                used_types=tuple(used_types),
                field_access=tuple(field_access),
                inheritance_info=tuple(inheritance_info),
                endpoint=tuple(endpoint),
                type = method_type,
                project_id=self.project_id,
                branch=self.branch
            )
        except Exception as e:
            logger.debug(f"Error processing method node: {e}")
            return None

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
            call_query = Query(self.language, """
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
            """)

            captures = QueryCursor(call_query).captures(method_node)

            call_nodes = captures.get("call", [])
            object_nodes = captures.get("object", [])
            method_nodes = captures.get("method_name", [])
            args_nodes = captures.get("arguments", [])

            for i, call_node in enumerate(call_nodes):
                object_node = object_nodes[i] if i < len(object_nodes) else None
                object_name = extract_content(object_node, content) if object_node else None

                if object_name and object_name in JavaBuiltinPackages.JAVA_PRIMITIVES:
                    continue

                try:
                    name_node = method_nodes[i] if i < len(method_nodes) else None
                    args_node = args_nodes[i] if i < len(args_nodes) else None

                    resolved = self._resolve_method_call(name_node, args_node, file_path, content)
                    if resolved:
                        # nếu MethodCall có field object_name thì gán
                        if object_name and hasattr(resolved, "object_name"):
                            resolved.object_name = object_name
                        method_calls.append(resolved)
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"Error extracting method calls: {e}")

        return method_calls


    def extract_local_variables(self, body_node: Node, file_path: str, content: str) -> Dict[str, str]:
        variables = {}

        try:
            # More comprehensive query
            var_query = Query(self.language, """
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
            """)

            captures = QueryCursor(var_query).captures(body_node)

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


    def _extract_used_types(self, body_node: Node, file_path: str, content: str, import_mapping: Dict[str, str]) -> List[str]:
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
                        variable_ref = import_mapping.get(text, self._resolve_used_type_with_lsp(node, file_path, text))
                        if variable_ref:
                            used_types.add(variable_ref)
        except Exception as e:
            logger.debug(f"Error extracting variable usage: {e}")
        return list(used_types)

    def _get_last_type_identifier(self, node: Node):
        type_identifiers = []

        def dfs(n):
            if n.type == "type_identifier":
                type_identifiers.append(n)
            for child in n.children:
                dfs(child)

        dfs(node)
        return type_identifiers[-1] if type_identifiers else node

    def _resolve_method_call(self, node, args, file_path: str, content):
        if not self.lsp_service:
            return None

        try:
            line = node.start_point[0]
            col = node.start_point[1]

            # args_val = extract_content(args, Path(file_path).read_text())
            lsp_result = self.lsp_service.request_definition(file_path, line, col)
            result = lsp_result[0]
            full_method_def = ""
            if isinstance(result, dict):
                raw_absolute_path = result.get('absolutePath')

                if raw_absolute_path and isinstance(raw_absolute_path, str):
                    absolute_path = self._strip_root(raw_absolute_path)
                    if not absolute_path:
                        return None
                    qualified_name = self.extract_method_with_params_from_lsp_result(result)
                    if not qualified_name:
                        return None
                    tree = self.parser.parse(bytes(content, 'utf8'))
                    class_nodes = self._extract_all_class_nodes(tree.root_node)
                    if class_nodes and len(class_nodes) > 1:
                        line = result.get('range').get('start').get('line')
                        col = result.get('range').get('start').get('character')
                        lsp_hover = self.lsp_service.request_hover(raw_absolute_path, line, col)
                        if not lsp_hover:
                            return None
                        method_value = lsp_hover.get('contents').get('value')
                        absolute_path = self._resolve_class_from_hover(method_value)
                        # request hover to get class name
                    full_method_def = f"{absolute_path}.{qualified_name}"
            if not full_method_def:
                return None
            params = []

            return MethodCall(
                name=full_method_def,
                params=params
            )

        except Exception as e:
            logger.debug(f"LSP method call resolution failed: {e}")
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

    def _resolve_used_type_with_lsp(self, node: Node, file_path: str, type_name: str) -> Optional[str]:
        if not self.lsp_service:
            return None

        try:
            line = node.start_point[0]
            col = node.start_point[1]

            lsp_results = self.lsp_service.request_definition(file_path, line, col)
            return self._resolve_lsp_type_response(lsp_results, type_name)

        except Exception as e:
            logger.debug(f"LSP variable resolution failed: {e}")
            return None

    def _resolve_field_access_with_lsp(self, node: Node, file_path: str) -> Optional[str]:
        if not self.lsp_service:
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

    # Inheritance Analysis
    def _build_inheritance_info(self, method_node: Node, method_name_node: Node, file_path: str) -> List[str]:
        for child in method_node.children:
            if child.type == 'body':
                return []

        line = method_name_node.start_point[0]
        col = method_name_node.start_point[1]
        logger.info(f'request_implementation {file_path}, {line}, {col}')
        lsp_results = self.lsp_service.request_implementation(file_path, line, col)
        logger.info(f'request_implementation 2 done')
        return self._resolve_lsp_method_implements(lsp_results)

    def _remove_prefix(self, path: str) -> str:
        prefix = "src.main.java."
        if path.startswith(prefix):
            path = path[len(prefix):]
        return path

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
            absolute_path = absolute_path.replace('\\\\', '.')
            return self._strip_root(absolute_path)
        except Exception as e:
            logger.debug(f"Failed to extract qualified name from LSP result: {e}")
            return ""

    def _get_absolute_path(self, absolute_path: str) -> str:
        if not absolute_path or not isinstance(absolute_path, str):
            logger.debug(f"Invalid absolute_path: {absolute_path}")
            return None

        abs_path = Path(absolute_path).resolve()
        root = Path(self.project_root).resolve()

        try:
            relative = abs_path.relative_to(root)
            return str(relative)
        except ValueError:
            return None

    def _strip_root(self, absolute_path: str) -> str:
        try:
            relative = self._get_absolute_path(absolute_path)
            if not relative:
                return ""

            result = str(relative).replace("\\\\",".").replace("\\", ".").replace("/", ".")
            if result.endswith(".java"):
                result = result[:-5]

            result = self._remove_prefix(result)
            return result
        except Exception as e:
            logger.debug(f"Error in _strip_root: {e}")
            return ""

    def filter(self, items: list) -> list:
        filtered, seen = [], set()

        for item in items:
            # Nếu là object có attribute name
            if hasattr(item, "name"):
                name = item.name
            elif isinstance(item, str):
                name = item
            else:
                continue

            # Loại primitive
            if name in JavaBuiltinPackages.JAVA_PRIMITIVES:
                continue

            # Loại built-in package
            if any(name.startswith(pkg + ".") or name == pkg for pkg in self.builtin_packages):
                continue

            if name.startswith("contents") or name.startswith("\\\\contents") or "contents.java.base" in name:
                continue

            # Tránh duplicate
            if name not in seen:
                filtered.append(item)
                seen.add(name)

        return filtered

    def _is_config_node(self, node: Node, content: str):
        is_config = False
        try:
            for child in node.children:
                if child.type != 'modifiers':
                    continue
                for grandchild in child.children:
                    if grandchild.type != 'annotation' and grandchild.type != 'marker_annotation':
                        continue
                    text = content[grandchild.start_byte:grandchild.end_byte]

                    if text in JavaParsingConstants.CONFIG_NODE_ANNOTATIONS:
                        is_config = True
                        break

            return is_config
        except Exception as ex:
            logger.warn(f"_is_config_class error {ex}")
            return None

    def build_import_mapping(self, class_node: Node, content: str) -> Dict[str, str]:

        import_mapping = {}

        try:
            # Query để extract import statements
            import_query = Query(self.language, """
               (import_declaration
                  [
                    (scoped_identifier) @import_path
                    (identifier) @import_path
                  ]
                ) @test
            """)

            query_cursor = QueryCursor(import_query)
            captures = query_cursor.captures(class_node)

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
