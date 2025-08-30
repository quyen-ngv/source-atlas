import logging
from pathlib import Path
from typing import Tuple, List, Dict

from tree_sitter import Parser, Language
from tree_sitter_languages import get_language

from analyzers.base_analyzer import BaseCodeAnalyzer
from models.domain_models import CodeChunk, DependencyGraph
from models.analyzer_config import AnalyzerConfig
from processors.java_processor import JavaFileProcessor
from utils.comment_remover import JavaCommentRemover
from utils.dependency_graph_builder import DependencyGraphBuilder
from utils.statistics_generator import StatisticsGenerator
from utils.result_exporter import ResultExporter
from utils.class_cache_builder import ClassCacheBuilder

logger = logging.getLogger(__name__)

class JavaCodeAnalyzer(BaseCodeAnalyzer):
    """Analyzer for Java projects, implementing the BaseCodeAnalyzer interface."""
    
    def __init__(self, config: AnalyzerConfig = None, lsp_service=None, root_path: str = None):
        super().__init__(config or AnalyzerConfig())
        
        # Initialize Tree-sitter components
        try:
            self.language: Language = get_language("java")
            self.parser = Parser()
            self.parser.set_language(self.language)
        except Exception as e:
            logger.error(f"Failed to initialize Tree-sitter for Java: {e}")
            raise
        
        # Initialize services
        self.comment_remover = JavaCommentRemover()
        self.file_processor = JavaFileProcessor(
            self.config, self.language, self.parser,
            lsp_service=lsp_service if config else None, project_root = root_path
        )
        self.dependency_graph_builder = DependencyGraphBuilder(self.config)
        self.statistics_generator = StatisticsGenerator()
        self.result_exporter = ResultExporter()
        self.class_cache_builder = ClassCacheBuilder(self.language, self.parser, self.comment_remover)
        
    def parse_project(self, root: Path, project_id: str) -> Tuple[List[CodeChunk], DependencyGraph]:
        """Parse a Java project directory."""
        logger.info(f"Starting to parse Java project: {project_id} at {root}")
        
        # Find all Java files
        java_files = list(root.rglob("*.java"))
        logger.info(f"Found {len(java_files)} Java files")
        
        if not java_files:
            logger.warning("No Java files found")
            return [], DependencyGraph()
        
        # Build class cache for type resolution
        logger.info("Building class cache for type resolution...")
        class_cache = self.class_cache_builder.build_class_cache(java_files)
        logger.info(f"Built class cache with {len(class_cache)} classes")
        
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
        """Export analysis results."""
        self.result_exporter.export_results(chunks, dependency_graph, output_path)
    
    def generate_statistics(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph) -> Dict:
        """Generate analysis statistics."""
        return self.statistics_generator.generate_statistics(chunks, dependency_graph)