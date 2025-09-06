from models.analyzer_config import AnalyzerConfig

class AnalyzerConfigBuilder:
    
    def __init__(self):
        self.config_data = {}
    
    def build(self, language: str) -> AnalyzerConfig:
        if language == "java":
            return AnalyzerConfig(**self.config_data)
        return AnalyzerConfig(**self.config_data)