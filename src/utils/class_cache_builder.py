import logging
from pathlib import Path
from typing import List, Set, Optional
from tree_sitter import Language, Parser, Node
from utils.comment_remover import JavaCommentRemover

logger = logging.getLogger(__name__)

class ClassCacheBuilder:
    """Builds cache of all available classes for type resolution."""
    
    def __init__(self, language: Language, parser: Parser, comment_remover: JavaCommentRemover):
        self.language = language
        self.parser = parser
        self.comment_remover = comment_remover
    
    def build_class_cache(self, files: List[Path]) -> Set[str]:
        """Build cache of all available classes."""
        class_cache = set()
        for file in files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                content = self.comment_remover.remove_comments(content)
                tree = self.parser.parse(bytes(content, 'utf8'))
                root_node = tree.root_node
                package = self._extract_package(root_node, content)
                class_nodes = self._extract_class_nodes(root_node)
                for class_node in class_nodes:
                    class_name = self._get_class_name(class_node, content)
                    if class_name:
                        parent_names = []
                        parent = class_node.parent
                        while parent and parent != root_node:
                            if parent.type in ['class_declaration', 'interface_declaration', 
                                             'enum_declaration', 'record_declaration']:
                                parent_name = self._get_class_name(parent, content)
                                if parent_name:
                                    parent_names.append(parent_name)
                            parent = parent.parent
                        if parent_names:
                            parent_names.reverse()
                            nested_path = '.'.join(parent_names + [class_name])
                            full_class_name = f"{package}.{nested_path}" if package else nested_path
                        else:
                            full_class_name = f"{package}.{class_name}" if package else class_name
                        class_cache.add(full_class_name)
            except Exception as e:
                logger.debug(f"Error building class cache for {file}: {e}")
                continue
        return class_cache
    
    def _extract_package(self, root_node: Node, content: str) -> str:
        try:
            package_query = self.language.query("""
                (package_declaration
                    (scoped_identifier) @package)
            """)
            captures = package_query.captures(root_node)
            if captures:
                package_node = captures[0][0]
                return content[package_node.start_byte:package_node.end_byte]
        except Exception:
            pass
        return ""
    
    def _extract_class_nodes(self, root_node: Node) -> List[Node]:
        try:
            class_query = self.language.query("""
                (class_declaration) @class
                (interface_declaration) @interface  
                (enum_declaration) @enum
                (record_declaration) @record
                (annotation_type_declaration) @annotation
            """)
            captures = class_query.captures(root_node)
            return [capture[0] for capture in captures]
        except Exception:
            return []
    
    def _get_class_name(self, class_node: Node, content: str) -> Optional[str]:
        try:
            for child in class_node.children:
                if child.type == 'identifier':
                    return content[child.start_byte:child.end_byte]
        except Exception:
            pass
        return None