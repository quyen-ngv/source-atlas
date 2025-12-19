import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Callable, Any

from loguru import logger
from tree_sitter import Language, Parser, Node

from source_atlas.lsp.lsp_service import LSPService
from source_atlas.models.domain_models import CodeChunk, ChunkType
from source_atlas.models.domain_models import Method
from source_atlas.utils.common import convert, read_file_content
from source_atlas.utils.lsp_utils import process_lsp_results


@dataclass
class ClassParsingContext:
    package: str
    class_name: str
    full_class_name: str
    is_nested: bool
    is_config: bool
    methods: List[str]
    import_mapping: Dict[str, str] = None
    parent_class: Optional[str] = None
    class_count: int = 1
    parsed_tree: Optional[Any] = None
    file_path: Optional[str] = None


class BaseCodeAnalyzer(ABC):

    def __init__(self, language: Language, parser: Parser, project_id: str, branch: str):
        self.language = language
        self.parser = parser
        self.comment_remover = None
        self.project_id = project_id
        self.branch = branch
        self.cached_nodes = {}
        self.methods_cache = set()
        self.lsp_service: Optional[LSPService] = None

    def parse_project(self, root: Path, target_files: Optional[List[str]] = None, parse_all: bool = True,
                      export_output: bool = True) -> List[CodeChunk]:
        logger.info(f"Starting analysis for project '{self.project_id}' at {root}")

        code_files = self._get_code_files(root)
        if not code_files:
            logger.warning("No source files found")
            return []

        # Filter files if parse_all is False and target_files is provided
        if not parse_all and target_files:
            code_files = self._filter_files_by_targets(code_files, target_files)

        if not code_files:
            logger.warning("No files to process after filtering")
            return []

        logger.info(f"Found {len(code_files)} source files to process")
        chunks: List[CodeChunk] = []

        # Build cache for all files (needed for cross-references)
        self.build_source_cache(root)

        # Process files sequentially (no threading for LSP compatibility)
        logger.info("Processing files sequentially")
        for i, file in enumerate(code_files, 1):
            try:
                file_chunks = self.process_file(file)
                chunks.extend(file_chunks)
                logger.debug(f"[{i}/{len(code_files)}] Completed processing: {file}")
            except Exception as e:
                logger.error(f"Error processing {file}: {e}", exc_info=True)

        logger.info(f"Extracted {len(chunks)} code chunks total")

        # Export to file if requested
        if export_output:
            output_path = Path("output") / str(self.project_id) / self.branch
            self.export_chunks(chunks, output_path)

        # Return chunks; higher layers (services) will handle persistence/indexing
        return chunks

    def process_file(self, file_path: Path) -> List[CodeChunk]:
        try:
            content = read_file_content(file_path)
            if not content.strip():
                return []

            content = self.comment_remover.remove_comments(content)

            # Check if we have a cached tree for this file
            tree = None
            for context in self.cached_nodes.values():
                if context.file_path == str(file_path) and context.parsed_tree is not None:
                    tree = context.parsed_tree
                    break
            
            # Parse tree only if not found in cache
            if tree is None:
                tree = self.parser.parse(bytes(content, 'utf8'))
            
            class_nodes = self._extract_all_class_nodes(tree.root_node)

            chunks = []
            for class_node in class_nodes:
                chunk = self._parse_class_node(class_node, content, str(file_path), tree.root_node)
                if chunk:
                    chunks.append(chunk)
            return chunks

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
            return []

    def _parse_class_node(self, class_node: Node, content: str, file_path: str, root_node: Node) -> Optional[CodeChunk]:
        try:
            with self.lsp_service.open_file(file_path):
                class_name = self._extract_class_name(class_node, content)
                package = self._extract_package(root_node, content)
                full_class_name = self._build_full_class_name(class_name, package, class_node, content, root_node)
                context = self.cached_nodes.get(full_class_name)
                if not context:
                    return None

                implements = []
                if self._should_check_implements(class_node, content):
                    implements = self._extract_implements_with_lsp(class_node, file_path, content)
                
                methods = self._extract_class_methods(
                    class_node, content, implements,
                    context.full_class_name, file_path, context.import_mapping
                )

                used_types = self.extract_class_use_types(class_node, content, file_path, context.import_mapping)

                is_annotation = self._is_annotation_declaration(class_node)
                annotations = self._extract_annotations(class_node, content, file_path, context.import_mapping)
                handles_annotation = self._detect_annotation_handler(class_node, content, file_path, context.import_mapping, implements)

                class_content = content[class_node.start_byte:class_node.end_byte]
                ast_hash = self.compute_ast_hash(class_content)

                return CodeChunk(
                    package=context.package,
                    class_name=context.class_name,
                    full_class_name=context.full_class_name,
                    file_path=file_path,
                    content=class_content,
                    ast_hash=ast_hash,
                    implements=implements,
                    methods=methods,
                    is_nested=context.is_nested,
                    parent_class=context.parent_class,
                    type=ChunkType.CONFIGURATION if context.is_config else ChunkType.REGULAR,
                    project_id=self.project_id,
                    branch=self.branch,
                    used_types=used_types,
                    is_annotation=is_annotation
                )
        except Exception as e:
            logger.error(f"Error parsing class node: {e}")
            return None

    def _build_class_context(self, class_node: Node, content: str, root_node: Node) -> Optional[ClassParsingContext]:
        class_name = self._extract_class_name(class_node, content)
        logger.info(f"class_name {class_name}")
        if not class_name:
            return None

        package = self._extract_package(root_node, content)
        is_nested = self._is_nested_class(class_node, root_node)
        full_class_name = self._build_full_class_name(class_name, package, class_node, content, root_node)
        parent_class = self._get_parent_class(class_node, content, package) if is_nested else None,
        is_config = self._is_config_node(class_node, content)
        import_mapping = self.build_import_mapping(root_node, content)
        
        # Extract and cache method names for this class
        methods = self._extract_all_method_names_from_class(class_node, content, full_class_name)
        self.methods_cache.update(methods)  # set.update() works with iterables
        
        return ClassParsingContext(
            package=package,
            class_name=class_name,
            full_class_name=full_class_name,
            is_nested=is_nested,
            parent_class=parent_class,
            is_config = is_config,
            import_mapping=import_mapping,
            methods=methods
        )

    def export_chunks(self, chunks: List[CodeChunk], output_path: Path) -> None:
        """Export chunks to JSON file"""
        if not chunks:
            logger.warning("No chunks to export")
            return
            
        logger.info(f"Exporting {len(chunks)} chunks to {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)
        
        chunks_data = [convert(c) for c in chunks]
        chunks_file = output_path / "chunks.json"
        
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Exported {len(chunks)} chunks to: {chunks_file}")

    def compute_ast_hash(self, code: str) -> str:
        """
        Compute AST hash for Java code using Tree-sitter.
        This method is specific to Java and uses the existing parser.
        """
        try:
            tree = self.parser.parse(bytes(code, "utf8"))
            root = tree.root_node

            def walk_ast(node):
                """Walk the AST and create a structural representation"""
                # Skip comments and whitespace nodes
                if node.type in ("comment", "block_comment", "line_comment", "line_comment", "modifiers"):
                    return ""

                # For leaf nodes, include the type but not the content
                if not node.children:
                    return f"{node.type}"

                # For internal nodes, include type and children
                children_repr = []
                for child in node.children:
                    child_repr = walk_ast(child)
                    if child_repr:  # Only include non-empty children
                        children_repr.append(child_repr)

                if children_repr:
                    return f"{node.type}({','.join(children_repr)})"
                else:
                    return f"{node.type}"

            ast_repr = walk_ast(root)
            return hashlib.sha256(ast_repr.encode()).hexdigest()

        except Exception as e:
            logger.debug(f"Error computing Java AST hash, falling back to normalized hash: {e}")
            # Fallback to normalized content hash
            return hashlib.sha256(code.encode()).hexdigest()


    @abstractmethod
    def _get_code_files(self, root: Path) -> List[Path]:

        pass

    @abstractmethod
    def _should_check_implements(self, class_node: Node, content: str) -> bool:
        pass

    @abstractmethod
    def _extract_all_class_nodes(self, root_node: Node) -> List[Node]:
        pass

    @abstractmethod
    def _extract_implements_with_lsp(self, class_node: Node, file_path: str, content: str) -> List[str]:
        pass

    @abstractmethod
    def _extract_class_methods(self, class_node: Node, content: str,
                               implements: List[str],
                               full_class_name: str, file_path: str, import_mapping: Dict[str, str]) -> List[Method]:
        pass

    @abstractmethod
    def _extract_class_name(self, class_node: Node, content: str) -> Optional[str]:
        pass

    @abstractmethod
    def _extract_package(self, root_node: Node, content: str) -> str:
        pass

    @abstractmethod
    def _is_nested_class(self, class_node: Node, root_node: Node) -> bool:
        pass

    @abstractmethod
    def _build_full_class_name(self, class_name: str, package: str, class_node: Node,
                               content: str, root_node: Node) -> str:
        pass

    @abstractmethod
    def _get_parent_class(self, class_node: Node, content: str, package: str) -> Optional[str]:
        pass

    @abstractmethod
    def _is_config_node(self, class_node: Node, content: str):
        pass

    @abstractmethod
    def build_import_mapping(self, root_node: Node, content: str) -> Dict[str, str]:
        pass


    @abstractmethod
    def _extract_all_method_names_from_class(self, class_node: Node, content: str, full_class_name: str) -> List[str]:
        pass


    @abstractmethod
    def extract_class_use_types(self, class_node, content, file_path, import_mapping: dict):
        pass

    @abstractmethod
    def _get_builtin_packages(self) -> List[str]:
        pass

    @abstractmethod
    def _strip_source_directory_prefix(self, path: str) -> str:
        pass

    def _extract_annotations(self, node: Node, content: str, file_path: str, import_mapping: Dict[str, str]) -> List[str]:
        return []

    def _detect_annotation_handler(self, node: Node, content: str, file_path: str, import_mapping: Dict[str, str], implements: List[str]) -> Optional[str]:
        return None

    def _is_annotation_declaration(self, node: Node) -> bool:
        return False

    # Concrete methods for reusability across language analyzers

    def filter_builtin_items(self, items: list) -> list:
        from source_atlas.config.java_constants import JavaBuiltinPackages
        
        filtered, seen = [], set()
        builtin_packages = self._get_builtin_packages()

        for item in items:
            # Extract name from object or use string directly
            if hasattr(item, "name"):
                name = item.name
            elif isinstance(item, str):
                name = item
            else:
                continue

            # Filter primitives (language-specific)
            if name in JavaBuiltinPackages.JAVA_PRIMITIVES:
                continue

            # Filter builtin packages
            if any(name.startswith(pkg + ".") or name == pkg for pkg in builtin_packages):
                continue

            # Filter invalid content paths
            if name.startswith("contents") or name.startswith("\\\\contents") or "contents.java.base" in name:
                continue

            # Avoid duplicates
            if name not in seen:
                filtered.append(item)
                seen.add(name)

        return filtered

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

    def _convert_absolute_to_relative_package_path(self, absolute_path: str) -> str:
        try:
            relative = self._get_absolute_path(absolute_path)
            if not relative:
                return ""

            result = str(relative).replace("\\\\", ".").replace("\\", ".").replace("/", ".")
            
            # Remove file extension
            if result.endswith(".java"):
                result = result[:-5]

            # Remove language-specific prefix
            result = self._strip_source_directory_prefix(result)
            return result
        except Exception as e:
            logger.debug(f"Error in _convert_absolute_to_relative_package_path: {e}")
            return ""

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
            return self._convert_absolute_to_relative_package_path(absolute_path)
        except Exception as e:
            logger.debug(f"Failed to extract qualified name from lsp result: {e}")
            return ""

    def _normalize_and_process_lsp_results(
        self, 
        lsp_results, 
        processor: Callable[[dict], Optional[str]]
    ) -> List[str]:
        return process_lsp_results(lsp_results, processor, log_errors=True)

    def _filter_files_by_targets(self, code_files: List[Path], target_files: Optional[List[str]]) -> List[Path]:
        if not target_files:
            return code_files
            
        filtered_files = []
        for code_file in code_files:
            code_file_str = str(code_file).replace('\\', '/')
            # Check if any target file path matches the end of this code file
            for target in target_files:
                target_normalized = target.replace('\\', '/')
                if code_file_str.endswith(target_normalized):
                    filtered_files.append(code_file)
                    break
        
        logger.info(f"Filtered to {len(filtered_files)} files based on target_files")
        return filtered_files

    def build_source_cache(self, root) -> Dict[str, ClassParsingContext]:
        # Get all code files and filter by target_files if provided
        code_files = self._get_code_files(root)
        cached_nodes = {}

        # Process cache building sequentially (no threading for LSP compatibility)
        logger.info("Building source cache sequentially")
        for i, file in enumerate(code_files, 1):
            try:
                cache_data = self.process_class_cache_file(file)
                cached_nodes.update(cache_data)
                logger.debug(f"[{i}/{len(code_files)}] Cached: {file}")
            except Exception as e:
                logger.error(f"Error caching {file}: {e}", exc_info=True)

        self.cached_nodes = cached_nodes
        logger.info(f"Cache built with {len(cached_nodes)} classes")
        return cached_nodes

    def process_class_cache_file(self, file_path) -> Dict[str, ClassParsingContext]:
        content = read_file_content(file_path)
        if not content.strip():
            return {}

        content = self.comment_remover.remove_comments(content)

        tree = self.parser.parse(bytes(content, 'utf8'))
        class_nodes = self._extract_all_class_nodes(tree.root_node)
        
        chunks = {}
        class_count = len(class_nodes)
        file_path_str = str(file_path)
        
        for class_node in class_nodes:
            context = self._build_class_context(class_node, content, tree.root_node)
            if context:
                # Store tree, class count, and file path for performance optimization
                context.parsed_tree = tree
                context.class_count = class_count
                context.file_path = file_path_str
                chunks[context.full_class_name] = context
        return chunks
