from typing import Dict, Any, List

from models.domain_models import CodeChunk, DependencyGraph


class StatisticsGenerator:
    """Generates comprehensive analysis statistics."""
    
    def generate_statistics(self, chunks: List[CodeChunk], dependency_graph: DependencyGraph) -> Dict:
        """Generate comprehensive analysis statistics."""
        stats = {
            'total_classes': len(chunks),
            'total_methods': sum(len(chunk.methods) for chunk in chunks),
            'dependency_stats': self._analyze_dependencies(dependency_graph),
            'package_distribution': self._analyze_packages(chunks),
            'complexity_metrics': self._calculate_complexity_metrics(chunks)
        }
        return stats
    
    def _analyze_dependencies(self, dependency_graph: DependencyGraph) -> Dict[str, Any]:
        dependency_types = {}
        for _, _, relation_type in dependency_graph.edges:
            dependency_types[relation_type] = dependency_types.get(relation_type, 0) + 1
        return {
            'total_dependencies': len(dependency_graph.edges),
            'dependency_types': dependency_types
        }
    
    def _analyze_packages(self, chunks: List[CodeChunk]) -> Dict[str, int]:
        packages = {}
        for chunk in chunks:
            package = chunk.package if chunk.package else '<default>'
            packages[package] = packages.get(package, 0) + 1
        return packages

    def _calculate_complexity_metrics(self, chunks: List[CodeChunk]) -> Dict[str, Any]:
        total_lines = 0
        max_methods_per_class = 0
        max_fields_per_class = 0
        avg_methods_per_class = 0
        avg_fields_per_class = 0
        if chunks:
            total_lines = sum(len(chunk.content.split('\n')) for chunk in chunks)
            max_methods_per_class = max(len(chunk.methods) for chunk in chunks)
            avg_methods_per_class = sum(len(chunk.methods) for chunk in chunks) / len(chunks)
        return {
            'total_lines_of_code': total_lines,
            'max_methods_per_class': max_methods_per_class,
            'max_fields_per_class': max_fields_per_class,
            'avg_methods_per_class': round(avg_methods_per_class, 2),
            'avg_fields_per_class': round(avg_fields_per_class, 2)
        }