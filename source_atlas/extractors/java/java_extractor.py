from typing import List

from tree_sitter import Node
from loguru import logger
from source_atlas.extractors.base_extractor import AnnotationDependencyExtractor
from source_atlas.extractors.java.kafka_extractor import KafkaAnnotationExtractor
from source_atlas.extractors.java.rabbit_extractor import RabbitAnnotationExtractor
from source_atlas.extractors.java.spring_event_extractor import EventAnnotationExtractor
from source_atlas.extractors.java.springboot_annotation_extractor import SpringBootAnnotationExtractor
from source_atlas.extractors.java.quarkus_extractor import QuarkusJaxRsExtractor
from source_atlas.models.domain_models import RestEndpoint


class JavaEndpointExtractor:
    """Extracts REST endpoint and pubsub/event info from Java methods."""

    def __init__(self, extractors: List[AnnotationDependencyExtractor] = None):
        """
        Initialize the extractor with a list of annotation extractors.
        
        Args:
            extractors: Optional list of extractors to use. If None, defaults to standard set.
        """
        if extractors is None:
            self.extractors = [
                SpringBootAnnotationExtractor(),
                QuarkusJaxRsExtractor(),
                KafkaAnnotationExtractor(),
                RabbitAnnotationExtractor(),
                EventAnnotationExtractor(),
            ]
        else:
            self.extractors = extractors

    def extract_from_method(self, method_node: Node, content: str, class_node: Node = None) -> List[RestEndpoint]:
        """
        Extract endpoint information from a method node.
        
        Args:
            method_node: The method AST node.
            content: The file content.
            class_node: The class AST node containing the method.
            
        Returns:
            List of extracted RestEndpoint objects.
        """
        endpoints: List[RestEndpoint] = []
        try:
            for child in method_node.children:
                if child.type != 'modifiers':
                    continue
                for grandchild in child.children:
                    if grandchild.type != 'annotation' and grandchild.type != 'marker_annotation':
                        continue

                    text = content[grandchild.start_byte:grandchild.end_byte]

                    for extractor in self.extractors:
                        if extractor.supports(text):
                            endpoints.extend(extractor.extract(text, class_node, method_node, content))
        except Exception as ex:
            logger.info(f"ex extract_from_method {ex}")

        return endpoints
