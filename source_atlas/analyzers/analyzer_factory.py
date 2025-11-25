from source_atlas.analyzers.java_analyzer import JavaCodeAnalyzer

from loguru import logger


class AnalyzerFactory:

    @staticmethod
    def create_analyzer(language: str, root_path: str = None, project_id: str = None, branch: str = None):
        logger.info(f"Creating analyzer for language: {language}, project_id: {project_id}, branch: {branch}")
        if language.lower() == "java":
            return JavaCodeAnalyzer(root_path, project_id, branch)
        raise ValueError(f"Unsupported language: {language}")
