from pathlib import Path
from typing import Optional

from analyzers.java_analyzer import JavaCodeAnalyzer
from analyzers.base_analyzer import BaseCodeAnalyzer
from models.analyzer_config import AnalyzerConfig
from factory.config_builder import AnalyzerConfigBuilder

class AnalyzerFactory:
    """Factory for creating language-specific code analyzers."""
    
    @staticmethod
    def create_analyzer(language: str, config: AnalyzerConfig, root_path: str = None):
        if language.lower() == "java":
            return JavaCodeAnalyzer(config, root_path)
        raise ValueError(f"Unsupported language: {language}")
