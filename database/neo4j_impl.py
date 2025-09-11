import uuid
import os
from neo4j import GraphDatabase
from neo4j.graph import Node
from typing import List, Dict, Tuple
from loguru import logger

from models.domain_models import CodeChunk

# Global Neo4j connection instance
_neo4j_connection = None

def get_neo4j_connection():
    """Get or create a global Neo4j connection instance"""
    global _neo4j_connection
    if _neo4j_connection is None:
        _neo4j_connection = Neo4jConnection()
    return _neo4j_connection

def close_neo4j_connection():
    """Close the global Neo4j connection"""
    global _neo4j_connection
    if _neo4j_connection is not None:
        _neo4j_connection.close()
        _neo4j_connection = None

def generate_uuid():
    return str(uuid.uuid4())

def escape_for_cypher(text):
    """Escape text for Cypher queries"""
    if text is None:
        return ""

    # Replace backslashes first (important order)
    text = text.replace('\\', '\\\\')
    # Replace quotes
    text = text.replace('"', '\\"')
    # Replace newlines
    text = text.replace('\n', '\\n')
    # Replace tabs
    text = text.replace('\t', '\\t')
    # Replace carriage returns
    text = text.replace('\r', '\\r')

    return text

def generate_cypher_from_json(chunks: List[CodeChunk], batch_size: int = 100) -> List[Tuple[str, Dict]]:
    """Generate Cypher queries with batch processing"""

    print(f"Processing {len(chunks)} chunks...")

    # Process in batches to avoid memory issues
    all_queries = []

    # Phase 1: Create all nodes using UNWIND for batch insert
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        node_data = []

        for chunk in batch:
            chunk = chunk.to_dict()
            file_path = chunk.get('file_path', '')
            class_name = chunk.get('full_class_name', '')
            content = escape_for_cypher(chunk.get('content', ''))

            # Determine node type
            if chunk.get('is_config_file'):
                node_type = "ConfigurationNode"
            else:
                node_type = "ClassNode"

            node_data.append({
                'node_type': node_type,
                'file_path': file_path,
                'class_name': class_name,
                'content': content,
            })

            # Process methods within this chunk
            methods = chunk.get('methods', [])
            for method in methods:
                method_file_path = chunk.get('file_path', '')
                method_class_name = chunk.get('full_class_name', '')
                method_name = method.get('name', '')
                method_body = escape_for_cypher(method.get('body', ''))
                method_field_access = str(method.get('field_access', []))
                method_content = method_body + " " + method_field_access

                # Determine method node type based on endpoint info
                endpoints = method.get('endpoint', [])
                if chunk.get('is_config_file'):
                    method_node_type = "ConfigurationNode"
                elif endpoints:
                    method_node_type = "EndpointNode"
                else:
                    method_node_type = "MethodNode"

                node_data.append({
                    'node_type': method_node_type,
                    'file_path': method_file_path,
                    'class_name': method_class_name,
                    'method_name': method_name,
                    'content': method_content,
                })

        # Create batch insert query
        batch_query = """
        UNWIND $nodes AS node
        CALL apoc.create.node([node.node_type], {
            file_path: node.file_path,
            class_name: node.class_name,
            method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
            content: node.content
        }) YIELD node AS created_node
        RETURN count(created_node)
        """

        all_queries.append((batch_query, {'nodes': node_data}))

    # Phase 2: Create relationships using batch processing
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]

        # Collect all relationships for this batch
        call_rels = []
        implement_rels = []
        extend_rels = []
        use_rels = []
        has_rels = []

        for chunk in batch:
            chunk = chunk.to_dict()
            chunk_class_name = chunk.get('full_class_name', '')

            # Process implements relationships at class level
            for impl in chunk.get('implements', []):
                implement_rels.append({
                    'source_class': chunk_class_name,
                    'target_class': impl
                })

            # Process extends relationships at class level
            extends = chunk.get('extends')
            if extends:
                extend_rels.append({
                    'source_class': chunk_class_name,
                    'target_class': extends
                })

            for used_method in chunk.get('methods', []):
                if used_method:
                    has_rels.append({
                        'source_class': chunk_class_name,
                        'target_method': used_method.get('name', '')
                    })

            # Process method-level relationships
            methods = chunk.get('methods', [])
            for method in methods:
                method_name = method.get('name', '')

                # CALL relationships from method_calls
                for call in method.get('method_calls', []):
                    call_name = call.get('name', '')
                    if call_name:
                        call_rels.append({
                            'source_class': chunk_class_name,
                            'source_method': method_name,
                            'target_method': call_name
                        })

                # IMPLEMENT relationships from inheritance_info
                for inheritance in method.get('inheritance_info', []):
                    if inheritance:
                        implement_rels.append({
                            'source_class': chunk_class_name,
                            'source_method': method_name,
                            'target_method': inheritance
                        })

                # USE relationships from used_types
                for used_type in method.get('used_types', []):
                    if used_type:
                        use_rels.append({
                            'source_class': chunk_class_name,
                            'source_method': method_name,
                            'target_class': used_type
                        })

        # Create batch queries for each relationship type
        if call_rels:
            call_query = """
            UNWIND $relationships AS rel
            MATCH (source {class_name: rel.source_class, method_name: rel.source_method})
            MATCH (target {method_name: rel.target_method})
            MERGE (source)-[:CALL]->(target)
            """
            all_queries.append((call_query, {'relationships': call_rels}))

        if implement_rels:
            # Handle class-level implements
            class_implement_rels = [rel for rel in implement_rels if 'source_method' not in rel]
            if class_implement_rels:
                class_implement_query = """
                UNWIND $relationships AS rel
                MATCH (source {class_name: rel.source_class})
                WHERE source.method_name IS NULL
                MATCH (target {class_name: rel.target_class})
                WHERE target.method_name IS NULL
                MERGE (source)-[:IMPLEMENT]->(target)
                """
                all_queries.append((class_implement_query, {'relationships': class_implement_rels}))

            # Handle method-level implements
            method_implement_rels = [rel for rel in implement_rels if 'source_method' in rel]
            if method_implement_rels:
                method_implement_query = """
                UNWIND $relationships AS rel
                MATCH (source {class_name: rel.source_class, method_name: rel.source_method})
                MATCH (target {method_name: rel.target_method})
                MERGE (source)-[:IMPLEMENT]->(target)
                """
                all_queries.append((method_implement_query, {'relationships': method_implement_rels}))

        if extend_rels:
            extend_query = """
            UNWIND $relationships AS rel
            MATCH (source {class_name: rel.source_class})
            WHERE source.method_name IS NULL
            MATCH (target {class_name: rel.target_class})
            WHERE target.method_name IS NULL
            MERGE (source)-[:EXTEND]->(target)
            """
            all_queries.append((extend_query, {'relationships': extend_rels}))

        if use_rels:
            use_query = """
            UNWIND $relationships AS rel
            MATCH (source {class_name: rel.source_class, method_name: rel.source_method})
            MATCH (target {class_name: rel.target_class})
            WHERE target.method_name IS NULL
            MERGE (source)-[:USE]->(target)
            """
            all_queries.append((use_query, {'relationships': use_rels}))

        if has_rels:
            use_query = """
            UNWIND $relationships AS rel
            MATCH (source {class_name: rel.source_class})
            MATCH (target {method_name: rel.target_method})
            WHERE target.method_name IS NOT NULL
            MERGE (source)-[:USE]->(target)
            """
            all_queries.append((use_query, {'relationships': has_rels}))

    return all_queries

class Neo4jConnection:
    def __init__(self):
        uri = os.getenv("APP_NEO4J_URI","bolt://localhost:7687")
        user = os.getenv("APP_NEO4J_USER","neo4j")
        password = os.getenv("APP_NEO4J_PASSWORD","your_password")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def execute_queries_batch(self, queries_with_params: List[Tuple[str, Dict]], max_retries: int = 3):
        """Execute queries with better error handling and memory management"""

        with self.driver.session() as session:
            for i, (query, params) in enumerate(queries_with_params):
                retry_count = 0

                while retry_count < max_retries:
                    try:
                        result = session.run(query, params)
                        # Consume result to free memory
                        result.consume()

                        print(f"Executed batch {i+1}/{len(queries_with_params)}")
                        break

                    except Exception as e:
                        retry_count += 1
                        print(f"Error executing batch {i+1} (attempt {retry_count}/{max_retries}): {str(e)}")

                        if retry_count >= max_retries:
                            print(f"Failed to execute batch {i+1} after {max_retries} attempts")
                            raise e

                        # Wait before retry
                        import time
                        time.sleep(1)

    def create_indexes(self):
        """Create indexes for better performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (n:EndpointNode) ON (n.class_name, n.method_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:MethodNode) ON (n.class_name, n.method_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ClassNode) ON (n.class_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:EndpointNode) ON (n.class_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:MethodNode) ON (n.class_name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ConfigurationNode) ON (n.class_name)",
        ]

        with self.driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                    print(f"Created index: {index_query}")
                except Exception as e:
                    print(f"Error creating index: {str(e)}")

    def import_code_chunks(self, chunks: List[CodeChunk], batch_size: int = 50):
        try:
            # Create indexes first for better performance
            print("Creating indexes...")
            self.create_indexes()

            # Generate optimized queries
            print("Generating optimized queries...")
            queries_with_params = generate_cypher_from_json(chunks, batch_size)

            print(f"Generated {len(queries_with_params)} batch queries")

            # Execute queries in batches
            print("Executing queries...")
            self.execute_queries_batch(queries_with_params)

            print("Import completed successfully!")

        except Exception as e:
            print(f"Error during import: {str(e)}")
            raise e

    def delete_project_data(self, project_id: str):
        """
        Delete all nodes and relationships for a specific project

        Args:
            project_id: The project ID to delete
        """
        try:
            with self.driver.session() as session:
                # First, get count of nodes to be deleted
                count_query = "MATCH (n) WHERE n.project_id = $project_id RETURN count(n) as node_count"
                result = session.run(count_query, {'project_id': project_id})
                node_count = result.single()['node_count']

                print(f"Found {node_count} nodes to delete for project: {project_id}")

                if node_count == 0:
                    print("No nodes found for this project ID")
                    return

                # Delete all nodes with the specified project_id
                # This will also delete all relationships connected to these nodes
                delete_query = """
                MATCH (n) 
                WHERE n.project_id = $project_id 
                DETACH DELETE n
                """

                result = session.run(delete_query, {'project_id': project_id})
                result.consume()

                print(f"Successfully deleted all nodes and relationships for project: {project_id}")

        except Exception as e:
            print(f"Error deleting project data: {str(e)}")
            raise e

    def delete_project_data_batch(self, project_id: str, batch_size: int = 1000):
        """
        Delete all nodes and relationships for a specific project in batches
        (Use this for large datasets to avoid memory issues)

        Args:
            project_id: The project ID to delete
            batch_size: Number of nodes to delete in each batch
        """
        try:
            with self.driver.session() as session:
                deleted_count = 0

                while True:
                    # Delete nodes in batches
                    delete_query = """
                    MATCH (n) 
                    WHERE n.project_id = $project_id 
                    WITH n LIMIT $batch_size
                    DETACH DELETE n
                    RETURN count(n) as deleted
                    """

                    result = session.run(delete_query, {
                        'project_id': project_id,
                        'batch_size': batch_size
                    })

                    batch_deleted = result.single()['deleted']
                    deleted_count += batch_deleted

                    print(f"Deleted {batch_deleted} nodes in this batch. Total deleted: {deleted_count}")

                    # If no nodes were deleted in this batch, we're done
                    if batch_deleted == 0:
                        break

                print(f"Successfully deleted {deleted_count} nodes and their relationships for project: {project_id}")

        except Exception as e:
            print(f"Error deleting project data in batches: {str(e)}")
            raise e

    def find_endpoint_node(self, class_name: str, method_name: str | None) -> List[Node]:
        logger.info(f"Finding endpoint node for class: {class_name}, method: {method_name}")
        with self.driver.session() as session:
            # Single query that handles both null and non-null method_name
            query = """
            MATCH path = (start)-[:IMPLEMENT|EXTEND|USED_BY|CALLED_BY*1..]->(endpoint:EndpointNode)
            WHERE start.class_name = $class_name 
            AND (
                ($method_name IS NULL AND start.method_name IS NULL) 
                OR 
                ($method_name IS NOT NULL AND start.method_name = $method_name)
            )
            RETURN DISTINCT endpoint
            """

            result = session.run(query, {
                'class_name': class_name,
                'method_name': method_name
            })

            return [record['endpoint'] for record in result]

    def find_related_nodes(self, class_name: str, method_name: str) -> List[Node]:
        logger.info(f"Finding related nodes for class: {class_name}, method: {method_name}")
        with self.driver.session() as session:
            query = """
            MATCH (endpoint:EndpointNode {class_name: $class_name, method_name: $method_name})
            CALL apoc.path.expandConfig(endpoint, {
                relationshipFilter: "CALL>|IMPLEMENTED_BY>|EXTENDED_BY>|IMPLEMENT|EXTEND|USE>",
                minLevel: 1,
                maxLevel: 20,
                bfs: true,
                uniqueness: "NODE_GLOBAL",
                filterStartNode: false
            }) YIELD path
            WITH path, nodes(path) AS node_list, relationships(path) AS rel_list
            WHERE NONE(i IN range(0, size(rel_list)-2) WHERE type(rel_list[i]) = 'USE' AND size(rel_list) > i + 1)
            UNWIND node_list AS node
            RETURN DISTINCT node
            """
            result = session.run(query, {'class_name': class_name, 'method_name': method_name})
            return [record['node'] for record in result]

    def find_configuration_node(self) -> List[Node]:
        with self.driver.session() as session:
            query = """
            MATCH (configuration:ConfigurationNode)
            RETURN configuration
            """
            result = session.run(query)
            return [record['configuration'] for record in result]