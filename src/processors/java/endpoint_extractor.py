import re
import logging
from typing import Optional, List, Protocol
from tree_sitter import Node
from models.domain_models import RestEndpoint
from models.analyzer_config import AnalyzerConfig

logger = logging.getLogger(__name__)


# ---- Dependency Extractor interface ----
class AnnotationDependencyExtractor(Protocol):
    def supports(self, annotation_text: str) -> bool: ...
    def extract(self, annotation_text: str, method_node: Node, content: str) -> List[RestEndpoint]: ...


# ---- REST extractor ----
class SpringBootAnnotationExtractor:
    def __init__(self, rest_annotations: dict):
        self.rest_annotations = rest_annotations

    def supports(self, text: str) -> bool:
        return any(anno in text for anno in self.rest_annotations.keys())

    def extract(self, text: str, method_node: Node, content: str) -> List[RestEndpoint]:
        method_path, type = "", None

        for anno, method in self.rest_annotations.items():
            if anno in text:
                path_match = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', text)
                if path_match:
                    method_path = path_match.group(1)
                else:
                    simple_path = re.search(r'@\w+\s*\(\s*["\']([^"\']*)["\']', text)
                    if simple_path:
                        method_path = simple_path.group(1)
                type = method
                if anno == '@RequestMapping':
                    method_match = re.search(r'method\s*=\s*RequestMethod\.(\w+)', text)
                    if method_match:
                        type = method_match.group(1)
                break

        if type:
            return [RestEndpoint(type=type, path=method_path)]
        return []


# ---- Kafka extractor ----
class KafkaAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@KafkaListener" in text

    def extract(self, text: str, method_node: Node, content: str) -> List[RestEndpoint]:
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


# ---- RabbitMQ extractor ----
class RabbitAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@RabbitListener" in text

    def extract(self, text: str, method_node: Node, content: str) -> List[RestEndpoint]:
        queues = []
        m = re.search(r'\bqueues\s*=\s*\{([^}]*)\}', text)
        if m:
            queues = [q.strip().strip('"\'') for q in m.group(1).split(",")]
        m = re.search(r'\bqueues\s*=\s*("([^"]+)"|\'([^\']+)\')', text)
        if m:
            queues.append(m.group(2) or m.group(3))
        return [RestEndpoint(type="RABBIT_CONSUMER", consumes=q) for q in queues]


# ---- Event extractor ----
class EventAnnotationExtractor:
    def supports(self, text: str) -> bool:
        return "@EventListener" in text

    def extract(self, text: str, method_node: Node, content: str) -> List[RestEndpoint]:
        classes = []
        m = re.search(r'\bclasses\s*=\s*\{([^}]*)\}', text)
        if m:
            classes = [c.strip().replace(".class", "") for c in m.group(1).split(",")]
        else:
            m = re.search(r'\bclasses\s*=\s*([A-Za-z_][\w\.]*\.class)', text)
            if m:
                classes = [m.group(1).replace(".class", "")]
        if not classes:
            # fallback: guess from method param
            for ch in method_node.children:
                if ch.type == 'formal_parameters':
                    params_src = content[ch.start_byte:ch.end_byte]
                    m = re.search(r'\(\s*([A-Za-z_][\w\.]*)\s+\w+', params_src)
                    if m:
                        classes = [m.group(1).split('.')[-1]]
                        break
        return [RestEndpoint(type="SPRING_EVENT_CONSUMER", consumes=ev) for ev in classes]


# ---- Main orchestrator ----
class JavaRestEndpointExtractor:
    """Extracts REST endpoint and pubsub/event info from Java methods."""

    def __init__(self, config: AnalyzerConfig):
        self.config = config
        self.extractors: List[AnnotationDependencyExtractor] = [
            SpringBootAnnotationExtractor(config.rest_annotations or {
                '@GetMapping': 'GET',
                '@PostMapping': 'POST',
                '@PutMapping': 'PUT',
                '@DeleteMapping': 'DELETE',
                '@PatchMapping': 'PATCH',
                '@RequestMapping': 'REQUEST',
            }),
            KafkaAnnotationExtractor(),
            RabbitAnnotationExtractor(),
            EventAnnotationExtractor(),
        ]

    def extract_from_method(self, method_node: Node, content: str, class_node: Node = None) -> List[RestEndpoint]:
        endpoints: List[RestEndpoint] = []

        for child in method_node.children:
            if child.type != 'modifiers':
                continue
            for grandchild in child.children:
                if grandchild.type != 'annotation':
                    continue

                text = content[grandchild.start_byte:grandchild.end_byte]

                for extractor in self.extractors:
                    if extractor.supports(text):
                        endpoints.extend(extractor.extract(text, method_node, content))

        # post-process REST (append class_path if any)
        for ep in endpoints:
            if ep.type in ("GET", "POST", "PUT", "DELETE", "PATCH", "REQUEST"):
                class_path = ""
                if class_node:
                    for child in class_node.children:
                        if child.type == 'modifiers':
                            for grandchild in child.children:
                                if grandchild.type == 'annotation':
                                    t = content[grandchild.start_byte:grandchild.end_byte]
                                    if '@RequestMapping' in t:
                                        m = re.search(r'(?:value\s*=\s*)?["\']([^"\']*)["\']', t)
                                        if m:
                                            class_path = m.group(1)
                if class_path and ep.path:
                    ep.path = class_path.rstrip("/") + "/" + ep.path.lstrip("/")
                elif class_path:
                    ep.path = class_path

        return endpoints
