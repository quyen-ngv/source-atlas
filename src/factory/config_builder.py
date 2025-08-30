from typing import Set, Dict, List
from models.analyzer_config import AnalyzerConfig

class AnalyzerConfigBuilder:
    """Builder pattern for creating analyzer configuration."""
    
    def __init__(self):
        self.config_data = {}
    
    def with_comment_removal(self, remove_comments: bool) -> 'AnalyzerConfigBuilder':
        self.config_data['remove_comments'] = remove_comments
        return self
    
    def with_custom_builtin_types(self, builtin_types: Set[str]) -> 'AnalyzerConfigBuilder':
        self.config_data['builtin_types'] = builtin_types
        return self
    
    def with_custom_job_patterns(self, patterns: List[str]) -> 'AnalyzerConfigBuilder':
        self.config_data['job_patterns'] = patterns
        return self
    
    def with_language_specific_config(self, language: str, config: Dict) -> 'AnalyzerConfigBuilder':
        self.config_data.setdefault('language_specific_configs', {})[language] = config
        return self
    
    def build(self) -> AnalyzerConfig:
        return AnalyzerConfig(**self.config_data)