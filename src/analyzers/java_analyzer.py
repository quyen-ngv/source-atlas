import logging
from pathlib import Path
from typing import Tuple, List, Dict

from tree_sitter import Parser, Language
from tree_sitter_language_pack import get_language

from analyzers.base_analyzer import BaseCodeAnalyzer
from lsp.implements.java_lsp import JavaLSPService
from models.domain_models import CodeChunk, DependencyGraph
from models.analyzer_config import AnalyzerConfig
from processors.java.java_processor import JavaFileProcessor
from utils.comment_remover import JavaCommentRemover
from utils.dependency_graph_builder import DependencyGraphBuilder
from utils.result_exporter import ResultExporter

logger = logging.getLogger(__name__)

class JavaCodeAnalyzer(BaseCodeAnalyzer):

    def __init__(self, config: AnalyzerConfig = None, root_path: str = None):
        super().__init__(config or AnalyzerConfig())
        
        # Initialize Tree-sitter components
        try:
            self.language: Language = get_language("java")
            self.parser = Parser(self.language)
        except Exception as e:
            logger.error(f"Failed to initialize Tree-sitter for Java: {e}")
            raise
        
        # Initialize services
        self.comment_remover = JavaCommentRemover()
        self.lsp_service = JavaLSPService.create(str(root_path))
        self._server_ctx = None   # để giữ context LSP

        self.file_processor = JavaFileProcessor(
            self.config, self.language, self.parser,
            lsp_service=self.lsp_service, project_root=root_path
        )
        self.dependency_graph_builder = DependencyGraphBuilder(self.config)
        self.result_exporter = ResultExporter()

    def __enter__(self):
        self._server_ctx = self.lsp_service.start_server()
        self._server_ctx.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._server_ctx:
            self._server_ctx.__exit__(exc_type, exc_val, exc_tb)
        
    def parse_project(self, root: Path, project_id: str) -> Tuple[List[CodeChunk], DependencyGraph]:
        logger.info(f"Starting to parse Java project: {project_id} at {root}")
        
        # Find all Java files
        java_files = list(root.rglob("*.java"))
        logger.info(f"Found {len(java_files)} Java files")
        
        if not java_files:
            logger.warning("No Java files found")
            return [], DependencyGraph()
                
        # Process files
        logger.info("Processing Java files...")
        chunks = []
        for i, java_file in enumerate(java_files):
            logger.debug(f"Processing file {i+1}/{len(java_files)}: {java_file}")
            file_chunks = self.file_processor.process_file(java_file, project_id)
            chunks.extend(file_chunks)
        
        logger.info(f"Processed {len(chunks)} classes/interfaces/enums")
        
        if not chunks:
            logger.warning("No classes were successfully parsed")
            return [], DependencyGraph()
        
        # Build dependency graph
        logger.info("Building dependency graph...")
        dependency_graph = self.dependency_graph_builder.build_dependency_graph(chunks)
        
        logger.info(f"Built dependency graph with {len(dependency_graph.nodes)} nodes and {len(dependency_graph.edges)} edges")
        
        return chunks, dependency_graph
    
    def export_results(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph, output_path: Path) -> None:
        self.result_exporter.export_results(chunks, dependency_graph, output_path)
    