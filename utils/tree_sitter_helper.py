from tree_sitter import Node


def extract_content(node: Node, content: str) -> str:
    return content[node.start_byte:node.end_byte]