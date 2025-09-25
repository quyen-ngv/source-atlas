import json
import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import List, Optional, Tuple, Dict

from tree_sitter import Language, Parser, Node

from database.neo4j_impl import get_neo4j_connection
from lsp.lsp_service import LSPService
from models.domain_models import CodeChunk, ChunkType
from models.domain_models import Method
from utils.common import convert

logger = logging.getLogger(__name__)


@dataclass
class ClassParsingContext:
    package: str
    class_name: str
    full_class_name: str
    is_nested: bool
    is_config: bool
    import_mapping: Dict[str, str] = None
    parent_class: Optional[str] = None


class BaseCodeAnalyzer(ABC):

    def __init__(self, language: Language, parser: Parser, project_id: str, branch: str):
        self.language = language
        self.parser = parser
        self.comment_remover = None
        self.max_workers = 16
        self.project_id = project_id
        self.branch = branch
        self.cached_nodes = {}
        self.methods_cache = {}
        self._lock = Lock()
        self.lsp_service: LSPService = None

    def parse_project(self, root: Path) -> List[CodeChunk]:
        logger.info(f"Starting analysis for project '{self.project_id}' at {root}")

        code_files = self._get_code_files(root)
        if not code_files:
            logger.warning("No source files found")
            return []

        logger.info(f"Found {len(code_files)} source files")
        chunks: List[CodeChunk] = []

        self.build_source_cache(root)

        # Process files sequentially
        for i, file in enumerate(code_files, 1):
            logger.debug(f"[{i}/{len(code_files)}] Processing file: {file}")

            try:
                file_chunks = self.process_file(file)
                chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}", exc_info=True)

        logger.info(f"Extracted {len(chunks)} code chunks total")

        self._build_knowledge_graph(chunks)
        return chunks

    def process_file(self, file_path: Path) -> List[CodeChunk]:
        try:
            content = self._read_file_content(file_path)
            if not content.strip():
                return []

            content = self.comment_remover.remove_comments(content)

            tree = self.parser.parse(bytes(content, 'utf8'))
            class_nodes = self._extract_all_class_nodes(tree.root_node)

            chunks = []
            for class_node in class_nodes:
                chunk = self._parse_class_node(class_node, content, str(file_path), tree.root_node)
                if chunk:
                    chunks.append(chunk)
            return chunks

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []

    def _parse_class_node(self, class_node: Node, content: str, file_path: str, root_node: Node) -> Optional[CodeChunk]:
        try:
            with self.lsp_service.open_file(file_path):
                class_name = self._extract_class_name(class_node, content)
                package = self._extract_package(root_node, content)
                full_class_name = self._build_full_class_name(class_name, package, class_node, content, root_node)
                context = self.cached_nodes[full_class_name]
                if not context:
                    return None

                implements = self._extract_implements_with_lsp(class_node, file_path, content)
                methods = self._extract_class_methods(
                    class_node, content, implements,
                    context.full_class_name, file_path, context.import_mapping
                )

                return CodeChunk(
                    package=context.package,
                    class_name=context.class_name,
                    full_class_name=context.full_class_name,
                    file_path=file_path,
                    content=content[class_node.start_byte:class_node.end_byte],
                    implements=implements,
                    methods=methods,
                    is_nested=context.is_nested,
                    parent_class=context.parent_class,
                    type=ChunkType.CONFIGURATION if context.is_config else ChunkType.REGULAR,
                    project_id=self.project_id,
                    branch=self.branch
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
        return ClassParsingContext(
            package=package,
            class_name=class_name,
            full_class_name=full_class_name,
            is_nested=is_nested,
            parent_class=parent_class,
            is_config = is_config,
            import_mapping=import_mapping
        )

    def _read_file_content(self, file_path: Path) -> str:
        """Read file content with encoding fallback."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin1') as f:
                return f.read()

    def export_chunks(self, chunks: List[CodeChunk], output_path: Path) -> None:

        logger.info(f"Exporting {len(chunks)} chunks to {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)
        chunks_data = [convert(c) for c in chunks]
        with open(output_path / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    @abstractmethod
    def _get_code_files(self, root: Path) -> List[Path]:
        """Return a list of relevant source files."""
        pass

    @abstractmethod
    def _extract_all_class_nodes(self, root_node: Node) -> List[Node]:
        pass

    @abstractmethod
    def _extract_implements_with_lsp(self, class_node: Node, file_path: str, content: str) -> List[str, ...]:
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

    def build_source_cache(self, root) -> Dict[str, ClassParsingContext]:
        code_files = self._get_code_files(root)
        cached_nodes = {}

        # Process files sequentially
        for i, file in enumerate(code_files, 1):
            logger.debug(f"[{i}/{len(code_files)}] Processing file: {file}")

            try:
                cache_data = self.process_class_cache_file(file)
                cached_nodes.update(cache_data)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}", exc_info=True)

        self.cached_nodes = cached_nodes
        return cached_nodes

    def process_class_cache_file(self, file_path) -> Dict[str, ClassParsingContext]:
        content = self._read_file_content(file_path)
        if not content.strip():
            return {}

        content = self.comment_remover.remove_comments(content)

        tree = self.parser.parse(bytes(content, 'utf8'))
        class_nodes = self._extract_all_class_nodes(tree.root_node)
        chunks = {}
        for class_node in class_nodes:
            context = self._build_class_context(class_node, content, tree.root_node)
            if context:
                chunks[context.full_class_name] = context
        return chunks

    def _build_knowledge_graph(self, chunks: List[CodeChunk]):
        neo4j_conn = get_neo4j_connection()
        neo4j_conn.import_code_chunks(chunks, 50)
        neo4j_conn.close()
        pass