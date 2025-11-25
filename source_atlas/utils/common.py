from dataclasses import asdict, is_dataclass
from enum import Enum

from pathlib import Path


def convert(obj):
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: convert(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [convert(v) for v in obj]
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    return obj


def normalize_whitespace(text):
    # Use regex to replace one or more whitespace characters with a single space
    import re
    # First, normalize all whitespace to single spaces
    text = re.sub(r'\s+', ' ', text).strip()
    # Then, remove spaces after '('
    text = re.sub(r'\(\s+', '(', text)
    # Remove spaces before ')'
    text = re.sub(r'\s+\)', ')', text)
    # Remove spaces after '<'
    text = re.sub(r'<\s+', '<', text)
    # Remove spaces before '>'
    text = re.sub(r'\s+>', '>', text)
    return text


def read_file_content(file_path: Path) -> str:
    """Read file content with encoding fallback."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, 'r', encoding='latin1') as f:
            return f.read()
