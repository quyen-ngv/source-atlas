import re

from typing import List

from source_atlas.models.domain_models import RestEndpoint
from tree_sitter import Node

class KafkaAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@KafkaListener" in text

    def extract(self, text: str, class_node: Node, method_node: Node, content: str) -> List[RestEndpoint]:
        topics = self._extract_kafka_topics(text)
        return [RestEndpoint(type="KAFKA_CONSUMER", consumes=t) for t in topics]

    def _extract_kafka_topics(self, text: str) -> List[str]:
        m = re.search(r'\btopics\s*=\s*\{([^}]*)\}', text)
        if m:
            return self._split_and_clean(m.group(1))

        m = re.search(r'\btopics\s*=\s*("([^"]+)"|\'([^\']+)\'|([A-Za-z_]\w*))', text)
        if m:
            return [self._clean_token(m.group(2) or m.group(3) or m.group(4))]

        m = re.search(r'@\s*KafkaListener\s*\(\s*(\{[^}]*\}|"(?:[^"]+)"|\'(?:[^\']+)\'|[A-Za-z_]\w*)', text)
        if m and 'topics=' not in text and 'topicPattern' not in text:
            arg = m.group(1).strip()
            if arg.startswith('{'):
                return self._split_and_clean(arg[1:-1])
            return [self._clean_token(arg)]

        m = re.search(r'\btopicPattern\s*=\s*("([^"]+)"|\'([^\']+)\')', text)
        if m:
            return [f"PATTERN:{self._clean_token(m.group(2) or m.group(3))}"]

        return []

    def _split_and_clean(self, s: str) -> List[str]:
        parts = re.split(r',\s*', s)
        return [self._clean_token(p) for p in parts if p.strip()]

    def _clean_token(self, t: str) -> str:
        t = t.strip().strip('"\'')
        return t.replace(".class", "").strip()