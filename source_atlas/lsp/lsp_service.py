from abc import ABC, abstractmethod
from typing import List, Optional, Tuple, Union, Iterator
from contextlib import contextmanager
from source_atlas.lsp.multilspy import multilspy_types
from source_atlas.lsp.multilspy.language_server import SyncLanguageServer
from source_atlas.lsp.multilspy.multilspy_config import MultilspyConfig
from source_atlas.lsp.multilspy.multilspy_logger import MultilspyLogger


class LSPService(ABC):
    """
    Abstract base class for Language Server Protocol services.
    
    This class provides a common interface for LSP operations while allowing
    language-specific implementations through abstract methods.
    """
    
    def __init__(self, language_server, timeout: Optional[int] = None):
        """
        Initialize the LSP service with a language server instance.
        
        :param language_server: The underlying language server instance
        :param timeout: Optional timeout for LSP requests
        """
        self.language_server = language_server
        self.timeout = timeout
    
    @classmethod
    def create(cls, repository_root_path: str) -> "LSPService":  
          config = MultilspyConfig.from_dict({"code_language": "java"}) # Also supports "python", "rust", "csharp", "typescript", "javascript", "go", "dart", "ruby"
          logger = MultilspyLogger()
          lsp = SyncLanguageServer.create(config, logger, repository_root_path)
          return lsp
    
    @contextmanager
    def start_server(self) -> Iterator["LSPService"]:
        """
        Start the language server and yield this service instance.
        """
        print('start server')
        with self.language_server.start_server():
            yield self
    
    @contextmanager
    def open_file(self, relative_file_path: str) -> Iterator[None]:
        """
        Open a file in the language server.
        
        :param relative_file_path: Relative path to the file
        """
        with self.language_server.open_file(relative_file_path):
            yield
    
 
    def request_definition(
        self, file_path: str, line: int, column: int
    ) -> List[multilspy_types.Location]:
        """
        Request symbol definition locations.
        
        :param file_path: Path to the file
        :param line: Line number (0-based)
        :param column: Column number (0-based)
        :return: List of definition locations
        """
        return self.language_server.request_definition(file_path, line, column)

    def request_hover(
        self, file_path: str, line: int, column: int
    ) -> List[multilspy_types.Location]:
        """
        Request symbol hover.
        
        :param file_path: Path to the file
        :param line: Line number (0-based)
        :param column: Column number (0-based)
        :return: List of hover
        """
        return self.language_server.request_hover(file_path, line, column)
    
    def request_implementation(
        self, file_path: str, line: int, column: int
    ) -> List[multilspy_types.Location]:
        """
        Request symbol implementation locations.
        
        :param file_path: Path to the file
        :param line: Line number (0-based)
        :param column: Column number (0-based)
        :return: List of implementation locations
        """
        return self.language_server.request_implementation(file_path, line, column)
    
    def request_references(
        self, file_path: str, line: int, column: int
    ) -> List[multilspy_types.Location]:
        """
        Request symbol reference locations.
        
        :param file_path: Path to the file
        :param line: Line number (0-based)
        :param column: Column number (0-based)
        :return: List of reference locations
        """
        return self.language_server.request_references(file_path, line, column)
