from abc import ABC, abstractmethod
import re
from typing import List, Set, Optional, Tuple

from models.analyzer_config import AnalyzerConfig

class BaseTypeResolver(ABC):
    """Abstract base class for type resolvers across different languages."""
    
    @abstractmethod
    def resolve_type_name(self, type_name: str, imports: dict, package: str) -> List[str]:
        """Resolve a type name to its fully qualified name."""
        pass

class JavaTypeResolver(BaseTypeResolver):
    """Resolves Java type names to fully qualified names."""
    
    def __init__(self, config: AnalyzerConfig, class_cache: Set[str]):
        self.config = config
        self.class_cache = class_cache
    
    def resolve_type_name(self, type_name: str, imports: dict, package: str) -> List[str]:
        """Resolve type name to fully qualified name."""
        if not type_name:
            return []
        
        array_suffix = ""
        if type_name.endswith('[]'):
            array_suffix = "[]"
            type_name = type_name[:-2].strip()
        
        generic_match = re.match(r'^([^<]+)', type_name)
        if generic_match:
            base_type, all_types, generic_part = self.extract_all_types_from_generic(type_name)
        else:
            base_type = type_name
            all_types = []
            generic_part = ""
        
        types = set()
        raw_types = {base_type} | set(all_types)
        
        java_lang_types = {
            'String', 'Object', 'Class', 'Integer', 'Long', 'Double', 'Float', 
            'Boolean', 'Character', 'Byte', 'Short', 'Number', 'Exception',
            'RuntimeException', 'Throwable', 'Error', 'Thread', 'Runnable'
        }
        
        for rt in raw_types:
            if rt in java_lang_types:
                types.add(rt)
            elif rt in self.config.builtin_types:
                types.add(rt)
            elif rt in imports:
                types.add(imports[rt])
            else:
                resolved = self._resolve_from_wildcard_imports(rt, imports)
                if resolved:
                    types.add(resolved + generic_part + array_suffix)
                elif package and rt[0].isupper():
                    same_package_type = f"{package}.{rt}"
                    if same_package_type in self.class_cache:
                        types.add(same_package_type + generic_part + array_suffix)
                    else:
                        types.add(rt + generic_part + array_suffix)
                else:
                    types.add(rt + generic_part + array_suffix)
        
        return list(types)
    
    def extract_all_types_from_generic(self, type_name: str) -> Tuple[str, List[str], str]:
        type_name = type_name.strip()
        base_match = re.match(r'^([^<]+)', type_name)
        if not base_match:
            return type_name, [], ""
        
        base_type = base_match.group(1).strip()
        if '<' not in type_name:
            return base_type, [], ""
        
        generic_start = type_name.find('<')
        generic_end = self.find_matching_bracket(type_name, generic_start)
        
        if generic_end == -1:
            return base_type, [], type_name[generic_start:]
        
        generic_content = type_name[generic_start + 1:generic_end]
        generic_part = type_name[generic_start:generic_end + 1]
        all_types = self.parse_generic_types(generic_content)
        
        return base_type, all_types, generic_part
    
    def find_matching_bracket(self, text: str, start_pos: int) -> int:
        if start_pos >= len(text) or text[start_pos] != '<':
            return -1
        bracket_count = 1
        pos = start_pos + 1
        while pos < len(text) and bracket_count > 0:
            if text[pos] == '<':
                bracket_count += 1
            elif text[pos] == '>':
                bracket_count -= 1
            pos += 1
        return pos - 1 if bracket_count == 0 else -1
    
    def parse_generic_types(self, generic_content: str) -> List[str]:
        if not generic_content.strip():
            return []
        return self.parse_generic_types_alternative(generic_content)
    
    def parse_generic_types_alternative(self, generic_content: str) -> List[str]:
        type_parts = self.split_by_top_level_comma(generic_content)
        types = []
        for part in type_parts:
            if part.strip():
                type_and_nested = self.extract_all_types_recursive(part.strip())
                types.extend(type_and_nested)
        return types
    
    def split_by_top_level_comma(self, content: str) -> List[str]:
        parts = []
        current_part = ""
        bracket_depth = 0
        for char in content:
            if char == '<':
                bracket_depth += 1
                current_part += char
            elif char == '>':
                bracket_depth -= 1
                current_part += char
            elif char == ',' and bracket_depth == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
            else:
                current_part += char
        if current_part.strip():
            parts.append(current_part.strip())
        return parts
    
    def extract_all_types_recursive(self, type_str: str) -> List[str]:
        type_str = type_str.strip()
        if not type_str:
            return []
        types = []
        base_match = re.match(r'^([^<]+)', type_str)
        if base_match:
            base_type = base_match.group(1).strip()
            clean_base = re.sub(r'\[\s*\]', '', base_type)
            clean_base = re.sub(r'^\?\s*(?:extends|super)\s+', '', clean_base)
            clean_base = clean_base.replace('?', '').strip()
            if clean_base and clean_base not in ['extends', 'super']:
                types.append(clean_base)
        if '<' in type_str:
            generic_start = type_str.find('<')
            generic_end = self.find_matching_bracket(type_str, generic_start)
            if generic_end != -1:
                generic_content = type_str[generic_start + 1:generic_end]
                nested_types = self.parse_generic_types(generic_content)
                types.extend(nested_types)
        return types
    
    def _resolve_from_wildcard_imports(self, class_name: str, imports: dict) -> Optional[str]:
        if not class_name or not class_name[0].isupper():
            return None
        wildcard_packages = [import_path for import_key, import_path in imports.items() 
                           if import_key.startswith('*')]
        for package in wildcard_packages:
            potential_full_name = f"{package}.{class_name}"
            if potential_full_name in self.class_cache or self._is_known_java_class(package, class_name):
                return potential_full_name
        return None
    
    def _is_known_java_class(self, package: str, class_name: str) -> bool:
        java_classes = {
            'java.util': {
                'List', 'Set', 'Map', 'Collection', 'ArrayList', 'LinkedList', 'HashSet', 
                'TreeSet', 'HashMap', 'TreeMap', 'LinkedHashMap', 'Vector', 'Stack',
                'Queue', 'Deque', 'PriorityQueue', 'Collections', 'Arrays', 'Optional',
                'Stream', 'Iterator', 'ListIterator', 'Enumeration', 'Properties',
                'Date', 'Calendar', 'GregorianCalendar', 'TimeZone', 'Locale',
                'Random', 'Scanner', 'StringTokenizer', 'Timer', 'TimerTask'
            },
            'java.io': {
                'File', 'FileInputStream', 'FileOutputStream', 'FileReader', 'FileWriter',
                'BufferedReader', 'BufferedWriter', 'PrintWriter', 'InputStream', 
                'OutputStream', 'Reader', 'Writer', 'IOException', 'FileNotFoundException',
                'ObjectInputStream', 'ObjectOutputStream', 'Serializable'
            },
            'java.time': {
                'LocalDate', 'LocalTime', 'LocalDateTime', 'ZonedDateTime', 'Instant',
                'Duration', 'Period', 'DateTimeFormatter', 'ZoneId', 'OffsetDateTime',
                'Year', 'Month', 'DayOfWeek', 'MonthDay', 'YearMonth'
            }
        }
        return package in java_classes and class_name in java_classes[package]