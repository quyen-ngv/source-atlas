import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Set, Optional

from models.analyzer_config import AnalyzerConfig
from models.domain_models import CodeChunk
from tree_sitter import Language, Parser, Node
from utils.comment_remover import BaseCommentRemover
from utils.type_resolver import BaseTypeResolver

logger = logging.getLogger(__name__)

class BaseFileProcessor(ABC):
    """Abstract base class for processing source code files of different languages."""
    
    def __init__(self, config: AnalyzerConfig, language: Language, parser: Parser):
        self.config = config
        self.language = language
        self.parser = parser
        self.comment_remover = None
    
    def process_file(self, file_path: Path, project_id: str) -> List[CodeChunk]:
        """Process a single Java file and return chunks for all classes/interfaces."""
        try:
            content = self._read_file_content(file_path)
            if not content.strip():
                return []
            
            if self.config.remove_comments:
                content = self.comment_remover.remove_comments(content)
            
            tree = self.parser.parse(bytes(content, 'utf8'))
            root_node = tree.root_node

            all_class_nodes = self._extract_all_class_nodes(root_node)
            chunks = []
            
            for class_node in all_class_nodes:
                chunk = self._parse_class_node(
                    class_node, content, str(file_path), root_node
                )
                if chunk:
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return []


    def _read_file_content(self, file_path: Path) -> str:
        """Read file content with encoding fallback."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin1') as f:
                return f.read()
    
    @abstractmethod
    def _parse_class_node(self, class_node: Node, content: str, file_path: str, root_node: Node) -> Optional[CodeChunk]:
        """Parse a single class/module node."""
        pass
