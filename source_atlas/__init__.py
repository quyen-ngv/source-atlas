"""
Source Atlas - Multi-language code analyzer with LSP and Neo4j integration.

This package provides tools for analyzing source code across multiple programming
languages, extracting code structures, and building knowledge graphs in Neo4j.
"""

__version__ = "0.1.0"
__author__ = "Nguyen Van Quyen"
__email__ = "quyennv.4work@gmail.com"
__license__ = "MIT"

# Public API
from source_atlas.analyzers.analyzer_factory import AnalyzerFactory
from source_atlas.models.domain_models import CodeChunk, Method, ChunkType
from source_atlas.neo4jdb.neo4j_service import Neo4jService

__all__ = [
    "AnalyzerFactory",
    "CodeChunk",
    "Method",
    "ChunkType",
    "Neo4jService",
]
