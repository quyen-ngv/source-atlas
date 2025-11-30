"""
LSP (Language Server Protocol) utility functions.

This module provides common utilities for processing LSP results,
reducing code duplication across language analyzers.
"""
from typing import Any, List, Optional, Dict, Callable
from loguru import logger


def normalize_lsp_results(lsp_results: Any) -> List[Any]:
    """
    Normalize LSP results to always return a list.
    
    Args:
        lsp_results: LSP result which could be None, a single result, or a list
        
    Returns:
        List of results, empty list if None
        
    Examples:
        >>> normalize_lsp_results(None)
        []
        >>> normalize_lsp_results({'uri': 'file.java'})
        [{'uri': 'file.java'}]
        >>> normalize_lsp_results([{'uri': 'file1.java'}, {'uri': 'file2.java'}])
        [{'uri': 'file1.java'}, {'uri': 'file2.java'}]
    """
    if not lsp_results:
        return []
    return lsp_results if isinstance(lsp_results, list) else [lsp_results]


def extract_file_path_from_lsp(lsp_result: Dict[str, Any]) -> Optional[str]:
    """
    Extract file path from LSP result.
    
    Args:
        lsp_result: LSP result dictionary
        
    Returns:
        File path string or None if not found
        
    Examples:
        >>> extract_file_path_from_lsp({'absolutePath': '/path/to/file.java'})
        '/path/to/file.java'
        >>> extract_file_path_from_lsp({'uri': 'file:///path/to/file.java'})
        '/path/to/file.java'
        >>> extract_file_path_from_lsp({})
        None
    """
    if not isinstance(lsp_result, dict):
        return None
        
    # Try 'absolutePath' first
    file_path = lsp_result.get('absolutePath')
    if file_path and isinstance(file_path, str):
        return file_path
        
    # Fall back to 'uri'
    uri = lsp_result.get('uri', '')
    if uri and isinstance(uri, str):
        # Remove file:// or file:/// prefix
        return uri.replace('file:///', '').replace('file://', '')
        
    return None


def extract_position_from_lsp(lsp_result: Dict[str, Any]) -> Optional[tuple]:
    """
    Extract line and column position from LSP result.
    
    Args:
        lsp_result: LSP result dictionary
        
    Returns:
        Tuple of (line, character) or None if not found
        
    Examples:
        >>> extract_position_from_lsp({'range': {'start': {'line': 10, 'character': 5}}})
        (10, 5)
        >>> extract_position_from_lsp({})
        None
    """
    if not isinstance(lsp_result, dict):
        return None
        
    range_info = lsp_result.get('range')
    if not range_info:
        return None
        
    start = range_info.get('start')
    if not start:
        return None
        
    line = start.get('line')
    character = start.get('character')
    
    if line is not None and character is not None:
        return (line, character)
        
    return None


def process_lsp_results(
    lsp_results: Any,
    processor: Callable[[Dict], Optional[str]],
    log_errors: bool = True
) -> List[str]:
    """
    Generic processor for LSP results.
    
    Normalizes results to a list and applies a processor function to each,
    filtering out None results.
    
    Args:
        lsp_results: Raw LSP results
        processor: Function to process each result, returns string or None
        log_errors: Whether to log processing errors
        
    Returns:
        List of processed strings (None values filtered out)
        
    Examples:
        >>> def get_path(r): return r.get('path')
        >>> results = [{'path': 'a.java'}, {'path': 'b.java'}, {}]
        >>> process_lsp_results(results, get_path)
        ['a.java', 'b.java']
    """
    normalized = normalize_lsp_results(lsp_results)
    processed = []
    
    for result in normalized:
        try:
            value = processor(result)
            if value:
                processed.append(value)
        except Exception as e:
            if log_errors:
                logger.debug(f"Error processing LSP result: {e}")
            continue
            
    return processed


def validate_lsp_result(lsp_result: Any) -> bool:
    """
    Validate that an LSP result has the expected structure.
    
    Args:
        lsp_result: LSP result to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not isinstance(lsp_result, dict):
        return False
        
    # Must have either absolutePath or uri
    has_path = (
        ('absolutePath' in lsp_result and isinstance(lsp_result['absolutePath'], str)) or
        ('uri' in lsp_result and isinstance(lsp_result['uri'], str))
    )
    
    return has_path
