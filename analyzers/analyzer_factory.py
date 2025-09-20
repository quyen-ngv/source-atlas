from analyzers.java_analyzer import JavaCodeAnalyzer


class AnalyzerFactory:

    @staticmethod
    def create_analyzer(language: str, root_path: str = None, project_id: str = None, branch: str = None):
        if language.lower() == "java":
            return JavaCodeAnalyzer(root_path, project_id, branch)
        raise ValueError(f"Unsupported language: {language}")
