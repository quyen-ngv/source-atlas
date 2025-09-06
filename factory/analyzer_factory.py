from analyzers.base_analyzer import BaseCodeAnalyzer
from analyzers.java_analyzer import JavaCodeAnalyzer


class AnalyzerFactory:

    @staticmethod
    def create_analyzer(language: str, root_path: str = None):
        if language.lower() == "java":
            return JavaCodeAnalyzer(root_path)
        raise ValueError(f"Unsupported language: {language}")
