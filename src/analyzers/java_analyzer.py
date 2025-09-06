import logging
from pathlib import Path
from typing import List

from analyzers.base_analyzer import BaseCodeAnalyzer
from lsp.implements.java_lsp import JavaLSPService
from models.analyzer_config import AnalyzerConfig
from models.domain_models import CodeChunk, DependencyGraph
from processors.java.java_processor import JavaFileProcessor
from tree_sitter import Parser, Language
from tree_sitter_language_pack import get_language
from utils.comment_remover import JavaCommentRemover

from factory.config_builder import AnalyzerConfigBuilder

logger = logging.getLogger(__name__)

class JavaCodeAnalyzerConstant:
    JAVA_CONFIG_EXTENSIONS = {
        "*.sql", "*.yml", "*.yaml", "*.xml"
    }

    JAVA_EXTENSION = "*.java"


class JavaCodeAnalyzer(BaseCodeAnalyzer):

    def __init__(self, root_path: str = None):
        config = AnalyzerConfigBuilder().build("java")
        super().__init__(config)

        # Tree-sitter setup
        self.language: Language = get_language("java")
        self.parser = Parser(self.language)

        # Services
        self.comment_remover = JavaCommentRemover()
        self.lsp_service = JavaLSPService.create(str(root_path))
        self._server_ctx = None
        self.file_processor = JavaFileProcessor(
            self.config, self.language, self.parser,
            lsp_service=self.lsp_service, project_root=root_path
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

    def _process_file(self, file_path: Path, project_id: str) -> List[CodeChunk]:
        return self.file_processor.process_file(file_path, project_id)
