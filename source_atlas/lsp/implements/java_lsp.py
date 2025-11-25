import os
import re
from typing import List, Optional

from source_atlas.lsp.lsp_service import LSPService
from source_atlas.lsp.multilspy.lsp_protocol_handler.lsp_types import HoverParams, TextDocumentIdentifier
from source_atlas.lsp.multilspy.multilspy_types import Position


class JavaLSPService(LSPService):
    """
    Java-specific implementation of the LSP service.
    """
    
    def get_language_id(cls) -> str:
        """Get the Java language identifier."""
        return "java"

    def find_java_classes_in_file(self, file_path: str) -> List[str]:
        """
        Find all Java class definitions in a file.
        
        :param file_path: Path to the Java file
        :return: List of class names
        """
        symbols, *_ = self.request_document_symbols(file_path)
        classes = []
        
        for symbol in symbols:
            if symbol.get('kind') == 5:  # CLASS_KIND
                classes.append(symbol.get('name', ''))
        
        return classes

    def find_java_methods_in_file(self, file_path: str) -> List[str]:
        """
        Find all Java method definitions in a file.
        
        :param file_path: Path to the Java file
        :return: List of method names
        """
        symbols, *_ = self.request_document_symbols(file_path)
        methods = []
        
        for symbol in symbols:
            if symbol.get('kind') == 6:  # METHOD_KIND
                methods.append(symbol.get('name', ''))
        
        return methods

    def find_java_interfaces_in_file(self, file_path: str) -> List[str]:
        """
        Find all Java interface definitions in a file.
        
        :param file_path: Path to the Java file
        :return: List of interface names
        """
        symbols, *_ = self.request_document_symbols(file_path)
        interfaces = []
        
        for symbol in symbols:
            if symbol.get('kind') == 11:  # INTERFACE_KIND
                interfaces.append(symbol.get('name', ''))
        
        return interfaces

    def _extract_package_from_file(self, file_path: str) -> str:
        """
        Extract package name from Java file.
        
        :param file_path: Path to the Java file
        :return: Package name or empty string if not found
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                package_match = re.search(r'package\s+([\w.]+)\s*;', content)
                return package_match.group(1) if package_match else ""
        except Exception:
            return ""

    def _format_java_identifier(self, location_info: dict, symbol_info: dict = None) -> str:
        """
        Format Java identifier based on location and symbol information.
        
        :param location_info: Location information from source_atlas.lsp response
        :param symbol_info: Optional symbol information for method details
        :return: Formatted Java identifier string
        """
        file_path = location_info.get('uri', '').replace('file://', '')
        
        # Extract package name
        package = self._extract_package_from_file(file_path)
        
        # Extract class name from file name
        class_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Build base identifier
        if package:
            base_identifier = f"{package}.{class_name}"
        else:
            base_identifier = class_name
        
        # If symbol_info is provided and it's a method, format accordingly
        if symbol_info and symbol_info.get('kind') == 6:  # METHOD_KIND
            method_name = symbol_info.get('name', '')
            
            # Try to extract parameter types from symbol detail if available
            detail = symbol_info.get('detail', '')
            param_types = self._extract_parameter_types(detail)
            
            if param_types:
                return f"{base_identifier}.{method_name}({','.join(param_types)})"
            else:
                return f"{base_identifier}.{method_name}()"
        
        # For classes and interfaces, return just the qualified name
        return base_identifier

    def _extract_parameter_types(self, method_signature: str) -> List[str]:
        """
        Extract parameter types from method signature.
        
        :param method_signature: Method signature string
        :return: List of parameter types
        """
        if not method_signature:
            return []
        
        # Match parameters within parentheses
        param_match = re.search(r'\(([^)]*)\)', method_signature)
        if not param_match:
            return []
        
        params_str = param_match.group(1).strip()
        if not params_str:
            return []
        
        # Split by comma and clean up parameter types
        param_types = []
        for param in params_str.split(','):
            param = param.strip()
            # Extract just the type (remove parameter name)
            type_match = re.search(r'^(\S+)', param)
            if type_match:
                param_types.append(type_match.group(1))
        
        return param_types

    def request_definition(self, file_path: str, line: int, character: int) -> str:
        """
        Request definition for symbol at given position.
        
        :param file_path: Path to the Java file
        :param line: Line number (0-based)
        :param character: Character position (0-based)
        :return: Formatted Java identifier string
        """
        try:
            # Request definition from source_atlas.lsp server
            definition_result = self.language_server.request_definition(file_path, line, character)
            
            if not definition_result:
                return ""
            
            # Handle both single location and array of locations
            locations = definition_result if isinstance(definition_result, list) else [definition_result]
            
            if not locations:
                return ""
            
            # Use the first location
            location = locations[0]
            
            # Get symbol information at the definition location
            def_file_path = location.get('uri', '').replace('file://', '')
            def_line = location.get('range', {}).get('start', {}).get('line', 0)
            def_char = location.get('range', {}).get('start', {}).get('character', 0)
            
            # Get document symbols to determine symbol type
            symbols, *_ = self.request_document_symbols(def_file_path)
            symbol_info = self._find_symbol_at_position(symbols, def_line, def_char)
            
            return self._format_java_identifier(location, symbol_info)
            
        except Exception as e:
            return f"Error requesting definition: {str(e)}"

    def request_implementation(self, file_path: str, line: int, character: int) -> str:
        """
        Request implementation for symbol at given position.
        
        :param file_path: Path to the Java file
        :param line: Line number (0-based)
        :param character: Character position (0-based)
        :return: Formatted Java identifier string
        """
        try:
            # Request implementation from source_atlas.lsp server
            return self.language_server.request_implementation(file_path, line, character)
            
        except Exception as e:
            return f"Error requesting implementation: {str(e)}"
    def request_hover(self, file_path: str, line: int, character: int) -> Optional[dict]:
        """
        Request hover information for symbol at given position.
        
        :param file_path: Path to the Java file
        :param line: Line number (0-based)
        :param character: Character position (0-based)
        :return: Hover information dictionary or None if not found
        """
        try:
            params = HoverParams(
                text_document=TextDocumentIdentifier(uri=f"file://{file_path}"),
                position=Position(line=line, character=character)
            )
            result = self.language_server.request_hover(params).result(timeout=10)
            if not result:
                return None
            return result
        except Exception as e:
            return None
    def request_references(self, file_path: str, line: int, character: int) -> str:
        """
        Request references for symbol at given position.
        Returns the first reference found.
        
        :param file_path: Path to the Java file
        :param line: Line number (0-based)
        :param character: Character position (0-based)
        :return: Formatted Java identifier string of first reference
        """
        try:
            # Request references from source_atlas.lsp server
            references_result = self.language_server.request_references(file_path, line, character, include_declaration=True)
            
            if not references_result:
                return ""
            
            # References should be a list of locations
            if not isinstance(references_result, list) or not references_result:
                return ""
            
            # Use the first reference
            location = references_result[0]
            
            # Get symbol information at the reference location
            ref_file_path = location.get('uri', '').replace('file://', '')
            ref_line = location.get('range', {}).get('start', {}).get('line', 0)
            ref_char = location.get('range', {}).get('start', {}).get('character', 0)
            
            # Get document symbols to determine symbol type
            symbols, *_ = self.request_document_symbols(ref_file_path)
            symbol_info = self._find_symbol_at_position(symbols, ref_line, ref_char)
            
            return self._format_java_identifier(location, symbol_info)
            
        except Exception as e:
            return f"Error requesting references: {str(e)}"

    def _find_symbol_at_position(self, symbols: List[dict], line: int, character: int) -> Optional[dict]:
        """
        Find symbol at specific line and character position.
        
        :param symbols: List of document symbols
        :param line: Line number
        :param character: Character position
        :return: Symbol information or None if not found
        """
        for symbol in symbols:
            symbol_range = symbol.get('range', {})
            start = symbol_range.get('start', {})
            end = symbol_range.get('end', {})
            
            start_line = start.get('line', 0)
            start_char = start.get('character', 0)
            end_line = end.get('line', 0)
            end_char = end.get('character', 0)
            
            # Check if position is within symbol range
            if (start_line <= line <= end_line and
                (line > start_line or character >= start_char) and
                (line < end_line or character <= end_char)):
                return symbol
            
            # Check children symbols recursively
            children = symbol.get('children', [])
            if children:
                child_symbol = self._find_symbol_at_position(children, line, character)
                if child_symbol:
                    return child_symbol
        
        return None