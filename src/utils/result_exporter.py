import json
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict

from models.domain_models import CodeChunk, DependencyGraph


class ResultExporter:
    """Exports analysis results to JSON files."""
    
    def export_results(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph, output_path: Path) -> None:
        """Export analysis results to JSON files."""
        output_path.mkdir(parents=True, exist_ok=True)
        self._export_chunks(chunks, output_path)
        self._export_dependency_graph(dependency_graph, output_path)
    
    def _export_chunks(self, chunks: List[CodeChunk], output_path: Path) -> None:
        chunks_data = []
        for chunk in chunks:
            chunk_dict = asdict(chunk)
            chunks_data.append(chunk_dict)
        with open(output_path / 'chunks.json', 'w', encoding='utf-8') as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)
    
    def _export_dependency_graph(self, dependency_graph: DependencyGraph, output_path: Path) -> None:
        # with open(output_path / 'dependency_graph.json', 'w', encoding='utf-8') as f:
        #     json.dump(dependency_graph.to_dict(), f, indent=2, ensure_ascii=False)
        pass
    