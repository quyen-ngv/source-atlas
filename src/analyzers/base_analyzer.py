from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List

from models.analyzer_config import AnalyzerConfig
from models.domain_models import CodeChunk, DependencyGraph


class BaseCodeAnalyzer(ABC):
    
    def __init__(self, config: AnalyzerConfig):
        self.config = config
    
    @abstractmethod
    def parse_project(self, root: Path, project_id: str) -> Tuple[List[CodeChunk], DependencyGraph]:
        """Parse a project directory and return code chunks and dependency graph."""
        pass
    
    @abstractmethod
    def export_results(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph, output_path: Path) -> None:
        """Export analysis results to the specified output path."""
        pass
