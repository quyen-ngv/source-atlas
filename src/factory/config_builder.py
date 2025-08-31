from typing import Set, Dict, List
from models.analyzer_config import AnalyzerConfig

class AnalyzerConfigBuilder:
    
    def __init__(self):
        self.config_data = {}
    
    def with_comment_removal(self, remove_comments: bool) -> 'AnalyzerConfigBuilder':
        self.config_data['remove_comments'] = remove_comments
        return self
    
    def build(self) -> AnalyzerConfig:
        return AnalyzerConfig(**self.config_data)