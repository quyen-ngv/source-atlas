import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from models.domain_models import CodeChunk
from tree_sitter import Language, Parser, Node

from models.domain_models import Method

logger = logging.getLogger(__name__)

@dataclass
class ClassParsingContext:
    package: str
    class_name: str
    full_class_name: str
    is_nested: bool
    parent_class: Optional[str] = None

class BaseCodeAnalyzer(ABC):

    def __init__(self, language: Language, parser: Parser):
        self.language = language
        self.parser = parser
        self.comment_remover = None

    def parse_project(self, root: Path, project_id: str) -> List[CodeChunk]:
        """
        Template method: orchestrates scanning and processing.
        Subclasses override `_get_code_files` and `_process_file`.
        """
        logger.info(f"Starting analysis for project '{project_id}' at {root}")

        code_files = self._get_code_files(root)
        if not code_files:
            logger.warning("No source files found")
            return []

        logger.info(f"Found {len(code_files)} source files")
        chunks: List[CodeChunk] = []

        for i, file in enumerate(code_files):
            logger.debug(f"[{i+1}/{len(code_files)}] Processing file: {file}")
            try:
                file_chunks = self.process_file(file, project_id)
                chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}", exc_info=True)

        logger.info(f"Extracted {len(chunks)} code chunks total")
        return chunks

    def process_file(self, file_path: Path, project_id: str) -> List[CodeChunk]:
        try:
            content = self._read_file_content(file_path)
            if not content.strip():
                return []

            content = self.comment_remover.remove_comments(content)

            tree = self.parser.parse(bytes(content, 'utf8'))
            class_nodes = self._extract_all_class_nodes(tree.root_node)

            logger.info(f"real file_path {str(file_path)}")
            return self._process_all_classes(class_nodes, content, str(file_path), tree.root_node)

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []

    def _process_all_classes(self, class_nodes: List[Node], content: str,
                             file_path: str, root_node: Node) -> List[CodeChunk]:
        chunks = []
        for class_node in class_nodes:
            chunk = self._parse_class_node(class_node, content, file_path, root_node)
            if chunk:
                chunks.append(chunk)
        return chunks

    def _parse_class_node(self, class_node: Node, content: str, file_path: str, root_node: Node) -> Optional[CodeChunk]:
        try:
            context = self._build_class_context(class_node, content, root_node)
            if not context:
                return None

            implements = self._extract_implements_with_lsp(class_node, file_path)
            extends = self._extract_extends_with_lsp(class_node, file_path)
            methods = self._extract_class_methods(
                class_node, content, implements, extends,
                context.full_class_name, file_path
            )

            return CodeChunk(
                package=context.package,
                class_name=context.class_name,
                full_class_name=context.full_class_name,
                file_path=file_path,
                content=content[class_node.start_byte:class_node.end_byte],
                implements=implements,
                extends=extends,
                methods=methods,
                is_nested=context.is_nested,
                parent_class=context.parent_class,
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
        parent_class=self._get_parent_class(class_node, content, package) if is_nested else None,

        return ClassParsingContext(
            package=package,
            class_name=class_name,
            full_class_name=full_class_name,
            is_nested=is_nested,
            parent_class=parent_class
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
        chunks_data = [asdict(c) for c in chunks]

        with open(output_path / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    # ---- extension points ----
    @abstractmethod
    def _get_code_files(self, root: Path) -> List[Path]:
        """Return a list of relevant source files."""
        pass

    @abstractmethod
    def _extract_all_class_nodes(self, root_node: Node) -> List[Node]:
        pass

    @abstractmethod
    def _extract_implements_with_lsp(self, class_node: Node, file_path: str) -> Tuple[str, ...]:
        pass

    @abstractmethod
    def _extract_extends_with_lsp(self, class_node: Node, file_path: str) -> Optional[str]:
        pass

    @abstractmethod
    def _extract_class_methods(self, class_node: Node, content: str,
                               implements: List[str], extends: Optional[str],
                               full_class_name: str, file_path: str) -> List[Method]:
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