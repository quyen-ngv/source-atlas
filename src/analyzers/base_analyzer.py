from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, List, Dict

from models.domain_models import CodeChunk, DependencyGraph
from models.analyzer_config import AnalyzerConfig

class BaseCodeAnalyzer(ABC):
    """Abstract base class for code analyzers across different programming languages."""
    
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
    
    @abstractmethod
    def generate_statistics(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph) -> Dict:
        """Generate analysis statistics for the project."""
        pass