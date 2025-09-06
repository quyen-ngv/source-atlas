from analyzers.base_analyzer import BaseCodeAnalyzer
from analyzers.java_analyzer import JavaCodeAnalyzer
from factory.config_builder import AnalyzerConfigBuilder
from models.analyzer_config import AnalyzerConfig


class AnalyzerFactory:

    @staticmethod
    def create_analyzer(language: str, root_path: str = None):
        if language.lower() == "java":
            return JavaCodeAnalyzer(root_path)
        raise ValueError(f"Unsupported language: {language}")
