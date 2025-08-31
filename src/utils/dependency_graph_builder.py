import logging
import re
from typing import List, Set

from models.domain_models import CodeChunk, DependencyGraph
from models.analyzer_config import AnalyzerConfig

logger = logging.getLogger(__name__)

class DependencyGraphBuilder:
    """Builds a dependency graph from code chunks."""
    
    def __init__(self, config: AnalyzerConfig):
        self.config = config
    
    def build_dependency_graph(self, chunks: List[CodeChunk]) -> DependencyGraph:
        """Build dependency graph from code chunks."""
        graph = DependencyGraph()
        try:
            for chunk in chunks:
                if not chunk.full_class_name:
                    continue
                
                # Add class node
                graph.add_node(chunk.full_class_name, chunk)
                
                # Add dependencies from extends
                if chunk.extends:
                    clean_type = self._clean_type_name(chunk.extends)
                    if clean_type and not self._is_builtin_type(clean_type):
                        graph.add_edge(chunk.full_class_name, clean_type, "extends")
                
                # Add dependencies from implements
                for interface in chunk.implements:
                    clean_type = self._clean_type_name(interface)
                    if clean_type and not self._is_builtin_type(clean_type):
                        graph.add_edge(chunk.full_class_name, clean_type, "implements")
                
                for method in chunk.methods:
                    
                    # Method calls
                    for call in method.method_calls:
                        target_class = call.rsplit(".", 1)[0] if "." in call else ""
                        clean_type = self._clean_type_name(target_class)
                        if clean_type and not self._is_builtin_type(clean_type):
                            graph.add_edge(chunk.full_class_name, clean_type, "method_call")
                    
                    # Variable usage
                    for var_type in method.variable_usage:
                        clean_type = self._clean_type_name(var_type)
                        if clean_type and not self._is_builtin_type(clean_type):
                            graph.add_edge(chunk.full_class_name, clean_type, "variable")
        
        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")
        
        return graph
    
    def _clean_type_name(self, type_name: str) -> str:
        """Remove generics and array brackets from type name."""
        if not type_name:
            return ""
        clean_type = type_name.replace('[]', '')
        generic_start = clean_type.find('<')
        if generic_start != -1:
            clean_type = clean_type[:generic_start]
        return clean_type.strip()
    
    def _is_builtin_type(self, type_name: str) -> bool:
        """Check if type is a built-in Java type."""
        if not type_name:
            return False
        base_type = type_name.split('.')[0] if '.' in type_name else type_name
        base_type = re.sub(r'<.*?>', '', base_type).replace('[]', '')
        return base_type in self.config.builtin_types or base_type.startswith('java.lang.')