from typing import List

from tree_sitter import Node

from extractors.base_extractor import AnnotationDependencyExtractor
from extractors.java.kafka_extractor import KafkaAnnotationExtractor
from extractors.java.rabbit_extractor import RabbitAnnotationExtractor
from extractors.java.spring_event_extractor import EventAnnotationExtractor
from extractors.java.springboot_annotation_extractor import SpringBootAnnotationExtractor
from models.domain_models import RestEndpoint


class JavaEndpointExtractor:
    """Extracts REST endpoint and pubsub/event info from Java methods."""

    def __init__(self):
        self.extractors: List[AnnotationDependencyExtractor] = [
            SpringBootAnnotationExtractor(),
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
                        endpoints.extend(extractor.extract(text, class_node, method_node, content))

        return endpoints
