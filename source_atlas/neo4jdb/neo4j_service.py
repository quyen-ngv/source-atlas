from typing import List, Dict, Tuple, Optional

from loguru import logger

from source_atlas.neo4jdb.neo4j_db import Neo4jDB
from source_atlas.neo4jdb.neo4j_dto import Neo4jNodeDto, Neo4jPathDto, Neo4jTraversalResultDto
from source_atlas.models.domain_models import CodeChunk, ChunkType
from source_atlas.config.config import configs


def _escape_for_cypher(text):
    if text is None:
        return ""
    text = text.replace('\\', '\\\\')
    text = text.replace('"', '\\"')
    text = text.replace('\n', '\\n')
    text = text.replace('\t', '\\t')
    text = text.replace('\r', '\\r')
    return text


def _node_to_dto(node) -> Neo4jNodeDto:
    """Convert Neo4j node to DTO"""
    if not node:
        return None

    node_dict = dict(node)
    return Neo4jNodeDto(
        id=node.id,
        labels=list(node.labels),
        properties=node_dict,
        **node_dict
    )


def _path_to_dto(path) -> Neo4jPathDto:
    """Convert Neo4j Path object to DTO"""
    if not path:
        return None

    nodes = [_node_to_dto(node) for node in path.nodes]
    relationships = []
    path_summary = []

    for i, rel in enumerate(path.relationships):
        start_node, end_node = _get_relationship_nodes(nodes, i)

        rel_data = _create_relationship_data(rel, start_node, end_node)
        relationships.append(rel_data)

        summary_item = _create_summary_item(i, rel, start_node, end_node)
        path_summary.append(summary_item)

    return Neo4jPathDto(
        start_node=nodes[0] if nodes else None,
        end_node=nodes[-1] if nodes else None,
        total_length=len(relationships),
        nodes=nodes,
        relationships=relationships,
        path_summary=path_summary
    )


def _get_relationship_nodes(nodes, index):
    """Get start and end nodes for a relationship at given index"""
    start_node = nodes[index] if index < len(nodes) else None
    end_node = nodes[index + 1] if index + 1 < len(nodes) else None
    return start_node, end_node


def _create_relationship_data(rel, start_node, end_node):
    """Create relationship data d"""

    return {
        "type": rel.type,
        "start_node": start_node,
        "end_node": end_node,
        "properties": dict(rel)
    }


def _create_summary_item(step_index, rel, start_node, end_node):
    """Create path summary item"""
    return {
        "step": step_index + 1,
        "from": _create_node_summary(start_node) if start_node else None,
        "relationship": rel.type,
        "to": _create_node_summary(end_node) if end_node else None
    }


def _create_node_summary(node):
    """Create node summary for path summary"""
    return {
        "class_name": node.class_name if node else None,
        "method_name": node.method_name if node else None,
        "node_type": node.labels[0] if node and node.labels else None
    }


class Neo4jService:
    def __init__(
        self, 
        db: Neo4jDB | None = None,
        url: str = None,
        user: str = None,
        password: str = None
    ):
        """
        Initialize Neo4j service.
        
        Args:
            db: Optional Neo4jDB instance. If provided, other arguments are ignored.
            url: Neo4j connection URL. If not provided, uses APP_NEO4J_URL env var.
            user: Neo4j username. If not provided, uses APP_NEO4J_USER env var.
            password: Neo4j password. If not provided, uses APP_NEO4J_PASSWORD env var.
            
        Raises:
            ValueError: If connection details are missing from both arguments and environment variables.
        """
        if db is not None:
            self.db = db
        else:
            # Resolve credentials from args or environment
            final_url = url or configs.APP_NEO4J_URL
            final_user = user or configs.APP_NEO4J_USER
            final_password = password or configs.APP_NEO4J_PASSWORD
            
            # Validate credentials
            if not all([final_url, final_user, final_password]):
                missing = []
                if not final_url: missing.append("URL")
                if not final_user: missing.append("User")
                if not final_password: missing.append("Password")
                
                raise ValueError(
                    f"Missing Neo4j credentials: {', '.join(missing)}. "
                    "Please provide them as arguments or set APP_NEO4J_URL, APP_NEO4J_USER, APP_NEO4J_PASSWORD environment variables."
                )
                
            self.db = Neo4jDB(url=final_url, user=final_user, password=final_password)

    def get_nodes_by_node_specs(self, node_specs: List[Dict], project_id: int, branch: str,
                                pull_request_id: Optional[str] = None) -> List[Neo4jNodeDto]:
        """Get nodes by list of node specifications"""
        if not node_specs:
            return []

        query = """
        UNWIND $node_specs AS spec
        MATCH (n {project_id: $project_id, branch: $branch, class_name: spec.class_name})
        WHERE ($pull_request_id IS NULL OR n.pull_request_id = $pull_request_id)
        AND (spec.method_name IS NULL OR n.method_name = spec.method_name)
        RETURN n
        """

        with self.db.driver.session() as session:
            result = session.run(query, {
                'node_specs': node_specs,
                'project_id': str(project_id),
                'branch': branch,
                'pull_request_id': pull_request_id
            })
            return [_node_to_dto(record['n']) for record in result]

    def create_indexes(self):
        indexes = [
            # Composite indexes for nodes
            "CREATE INDEX IF NOT EXISTS FOR (n:EndpointNode) ON (n.class_name, n.method_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:MethodNode) ON (n.class_name, n.method_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ClassNode) ON (n.class_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ConfigurationNode) ON (n.class_name, n.project_id, n.branch)",
            # Project and branch indexes
            "CREATE INDEX IF NOT EXISTS FOR (n:EndpointNode) ON (n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:MethodNode) ON (n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ClassNode) ON (n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ConfigurationNode) ON (n.project_id, n.branch)",
        ]

        with self.db.driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    logger.error(f"Error creating index: {str(e)}")

    def generate_cypher_from_chunks(self, chunks: List[CodeChunk], batch_size: int = 100,
                                    main_branch: Optional[str] = None,
                                    base_branch: Optional[str] = None, pull_request_id: Optional[str] = None) -> \
            List[Tuple[str, Dict]]:
        all_queries = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            node_data = []
            class_nodes_to_delete = []
            method_nodes_to_delete = []

            for chunk in batch:
                file_path = chunk.file_path
                class_name = chunk.full_class_name
                content = _escape_for_cypher(chunk.content)
                node_type = "ConfigurationNode" if chunk.type == ChunkType.CONFIGURATION else "ClassNode"

                # Collect class node for deletion
                class_nodes_to_delete.append({
                    'class_name': class_name,
                    'project_id': str(chunk.project_id),
                    'branch': chunk.branch
                })

                node_data_item = {
                    'node_type': node_type,
                    'file_path': file_path,
                    'class_name': class_name,
                    'content': content,
                    'ast_hash': chunk.ast_hash,
                    'project_id': str(chunk.project_id),
                    'branch': chunk.branch
                }

                # Add pull_request_id if branch is not main_branch
                if pull_request_id and chunk.branch != main_branch:
                    node_data_item['pull_request_id'] = pull_request_id

                node_data.append(node_data_item)

                for method in chunk.methods:
                    method_file_path = chunk.file_path
                    method_class_name = chunk.full_class_name
                    method_name = method.name
                    method_body = _escape_for_cypher(method.body)
                    method_field_access = str(method.field_access)
                    method_content = method_body + " " + method_field_access
                    if method.type == ChunkType.CONFIGURATION:
                        method_node_type = "ConfigurationNode"
                    elif method.type == ChunkType.ENDPOINT:
                        method_node_type = "EndpointNode"
                    else:
                        method_node_type = "MethodNode"

                    # Collect method node for deletion
                    method_nodes_to_delete.append({
                        'class_name': method_class_name,
                        'method_name': method_name,
                        'project_id': str(method.project_id),
                        'branch': method.branch
                    })

                    method_node_data_item = {
                        'node_type': method_node_type,
                        'file_path': method_file_path,
                        'class_name': method_class_name,
                        'method_name': method_name,
                        'content': method_content,
                        'ast_hash': method.ast_hash,
                        'project_id': str(method.project_id),
                        'branch': method.branch,
                        'endpoint': str(method.endpoint) if method.endpoint else None
                    }

                    # Add pull_request_id if branch is not main_branch
                    if pull_request_id and method.branch != main_branch:
                        method_node_data_item['pull_request_id'] = pull_request_id

                    node_data.append(method_node_data_item)

                # Delete existing nodes - include pull_request_id in matching if provided
                if class_nodes_to_delete:
                    # Delete class nodes by branch only
                    delete_class_query = """
                    UNWIND $nodes AS node
                    MATCH (n {class_name: node.class_name, project_id: node.project_id, branch: node.branch})
                    WHERE n.method_name IS NULL AND n.pull_request_id IS NULL
                    DETACH DELETE n
                    """
                    all_queries.append((delete_class_query, {'nodes': class_nodes_to_delete}))

                if method_nodes_to_delete:
                    # Delete method nodes by branch only
                    delete_method_query = """
                    UNWIND $nodes AS node
                    MATCH (n {class_name: node.class_name, method_name: node.method_name, project_id: node.project_id, branch: node.branch})
                    WHERE n.method_name IS NOT NULL AND n.pull_request_id IS NULL
                    DETACH DELETE n
                    """
                    all_queries.append((delete_method_query, {'nodes': method_nodes_to_delete}))

            # Create new nodes with smart duplicate checking
            if main_branch and base_branch:
                batch_query = """
                UNWIND $nodes AS node
                // Tìm node tương ứng trong main_branch
                OPTIONAL MATCH (main_node {
                    class_name: node.class_name,
                    project_id: node.project_id,
                    branch: $main_branch,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END
                })
                
                // Tìm node tương ứng trong base_branch
                OPTIONAL MATCH (base_node {
                    class_name: node.class_name,
                    project_id: node.project_id,
                    branch: $base_branch,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END
                })
                
                // Điều kiện lọc - chỉ tạo node mới khi thỏa mãn các điều kiện
                WITH node, main_node, base_node
                WHERE 
                    // ✅ TH1: Có base_branch, so sánh với base_branch bằng AST hash
                    (base_node IS NOT NULL AND node.ast_hash <> base_node.ast_hash)
                    OR
                    // ✅ TH2: Không có base_branch, so sánh với main_branch bằng AST hash
                    (base_node IS NULL AND main_node IS NOT NULL AND node.ast_hash <> main_node.ast_hash)
                    OR
                    // ✅ TH3: Node hoàn toàn mới - chưa tồn tại ở cả base và main
                    (base_node IS NULL AND main_node IS NULL)
                
                // Tạo node mới
                CALL apoc.create.node([node.node_type], {
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content,
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    pull_request_id: CASE WHEN node.pull_request_id IS NOT NULL THEN node.pull_request_id ELSE null END,
                    endpoint: CASE WHEN node.endpoint IS NOT NULL THEN node.endpoint ELSE null END
                }) YIELD node AS created_node
                RETURN count(created_node) AS created_count
                """
                all_queries.append(
                    (batch_query, {'nodes': node_data, 'main_branch': main_branch, 'base_branch': base_branch}))
            elif main_branch:
                # Fallback logic khi chỉ có main_branch
                batch_query = """
                UNWIND $nodes AS node
                OPTIONAL MATCH (main_node {
                    class_name: node.class_name,
                    project_id: node.project_id,
                    branch: $main_branch,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END
                })
                WHERE main_node IS NULL OR main_node.ast_hash <> node.ast_hash
                CALL apoc.create.node([node.node_type], {
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content,
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    pull_request_id: CASE WHEN node.pull_request_id IS NOT NULL THEN node.pull_request_id ELSE null END,
                    endpoint: CASE WHEN node.endpoint IS NOT NULL THEN node.endpoint ELSE null END
                }) YIELD node AS created_node
                RETURN count(created_node)
                """
                all_queries.append((batch_query, {'nodes': node_data, 'main_branch': main_branch}))
            else:
                batch_query = """
                UNWIND $nodes AS node
                CALL apoc.create.node([node.node_type], {
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content, 
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    pull_request_id: CASE WHEN node.pull_request_id IS NOT NULL THEN node.pull_request_id ELSE null END,
                    endpoint: CASE WHEN node.endpoint IS NOT NULL THEN node.endpoint ELSE null END
                }) YIELD node AS created_node
                RETURN count(created_node)
                """
                all_queries.append((batch_query, {'nodes': node_data}))

        # Relationships
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            call_rels = []
            implement_rels = []
            use_rels = []
            for chunk in batch:
                chunk_class_name = chunk.full_class_name
                chunk_project_id = str(chunk.project_id)
                chunk_branch = chunk.branch

                # Add class-level USE relationships for field types
                if hasattr(chunk, 'used_types') and chunk.used_types:
                    for used_type in chunk.used_types:
                        if used_type:
                            use_rels.append({
                                'source_class': chunk_class_name,
                                'target_class': used_type,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch
                            })

                for impl in chunk.implements:
                    implement_rels.append({
                        'source_class': impl,
                        'target_class': chunk_class_name,
                        'project_id': chunk_project_id,
                        'branch': chunk_branch
                    })
                for method in chunk.methods:
                    method_name = method.name
                    for call in method.method_calls:
                        call_name = call.name
                        if call_name:
                            call_rels.append({
                                'source_class': chunk_class_name,
                                'source_method': method_name,
                                'target_method': call_name,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch
                            })
                    for inheritance in method.inheritance_info:
                        if inheritance:
                            implement_rels.append({
                                'source_method': inheritance,
                                'target_class': chunk_class_name,
                                'target_method': method_name,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch
                            })
                    for used_type in method.used_types:
                        if used_type:
                            use_rels.append({
                                'source_class': chunk_class_name,
                                'source_method': method_name,
                                'target_class': used_type,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch
                            })

            if call_rels:
                if main_branch:
                    # Use base_branch first, then fallback to main_branch
                    call_query = """
                    UNWIND $relationships AS rel
                    MATCH (source {class_name: rel.source_class, method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                    OPTIONAL MATCH (target_base {method_name: rel.target_method, project_id: rel.project_id, branch: $base_branch})
                    OPTIONAL MATCH (target_main {method_name: rel.target_method, project_id: rel.project_id, branch: $main_branch})
                    WITH source, COALESCE(target_base, target_main) AS target
                    WHERE target IS NOT NULL
                    MERGE (source)-[:CALL]->(target)
                    """
                    all_queries.append((call_query, {'relationships': call_rels, 'base_branch': base_branch,
                                                     'main_branch': main_branch}))
                else:
                    call_query = """
                    UNWIND $relationships AS rel
                    MATCH (source {class_name: rel.source_class, method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                    MATCH (target {method_name: rel.target_method, project_id: rel.project_id, branch: rel.branch})
                    MERGE (source)-[:CALL]->(target)
                    """
                    all_queries.append((call_query, {'relationships': call_rels}))

            if implement_rels:
                class_implement_rels = [rel for rel in implement_rels if 'source_method' not in rel]
                if class_implement_rels:
                    if main_branch:
                        class_implement_query = """
                        UNWIND $relationships AS rel
                        OPTIONAL MATCH (source_base {class_name: rel.source_class, project_id: rel.project_id, branch: $base_branch})
                        WHERE source_base.method_name IS NULL
                        OPTIONAL MATCH (source_main {class_name: rel.source_class, project_id: rel.project_id, branch: $main_branch})
                        WHERE source_main.method_name IS NULL
                        WITH rel, COALESCE(source_base, source_main) AS source
                        WHERE source IS NOT NULL
                        OPTIONAL MATCH (target_base {class_name: rel.target_class, project_id: rel.project_id, branch: $base_branch})
                        WHERE target_base.method_name IS NULL
                        OPTIONAL MATCH (target_main {class_name: rel.target_class, project_id: rel.project_id, branch: $main_branch})
                        WHERE target_main.method_name IS NULL
                        WITH source, COALESCE(target_base, target_main) AS target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:IMPLEMENT]->(target)
                        """
                        all_queries.append((class_implement_query,
                                            {'relationships': class_implement_rels, 'base_branch': base_branch,
                                             'main_branch': main_branch}))
                    else:
                        class_implement_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE source.method_name IS NULL
                        MATCH (target {class_name: rel.target_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE target.method_name IS NULL
                        MERGE (source)-[:IMPLEMENT]->(target)
                        """
                        all_queries.append((class_implement_query, {'relationships': class_implement_rels}))

                method_implement_rels = [rel for rel in implement_rels if 'source_method' in rel]
                if method_implement_rels:
                    if main_branch:
                        method_implement_query = """
                        UNWIND $relationships AS rel
                        OPTIONAL MATCH (source_base {method_name: rel.source_method, project_id: rel.project_id, branch: $base_branch})
                        OPTIONAL MATCH (source_main {method_name: rel.source_method, project_id: rel.project_id, branch: $main_branch})
                        WITH rel, COALESCE(source_base, source_main) AS source
                        WHERE source IS NOT NULL
                        OPTIONAL MATCH (target_base {class_name: rel.target_class, method_name: rel.target_method, project_id: rel.project_id, branch: $base_branch})
                        OPTIONAL MATCH (target_main {class_name: rel.target_class, method_name: rel.target_method, project_id: rel.project_id, branch: $main_branch})
                        WITH source, COALESCE(target_base, target_main) AS target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:IMPLEMENT]->(target)
                        """
                        all_queries.append((method_implement_query,
                                            {'relationships': method_implement_rels, 'base_branch': base_branch,
                                             'main_branch': main_branch}))
                    else:
                        method_implement_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                        MATCH (target {class_name: rel.target_class, method_name: rel.target_method, project_id: rel.project_id, branch: rel.branch})
                        MERGE (source)-[:IMPLEMENT]->(target)
                        """
                        all_queries.append((method_implement_query, {'relationships': method_implement_rels}))

            if use_rels:
                # Separate class-level and method-level USE relationships
                class_use_rels = [rel for rel in use_rels if 'source_method' not in rel]
                method_use_rels = [rel for rel in use_rels if 'source_method' in rel]

                # Handle class-level USE relationships
                if class_use_rels:
                    if main_branch:
                        class_use_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE source.method_name IS NULL
                        OPTIONAL MATCH (target_base {class_name: rel.target_class, project_id: rel.project_id, branch: $base_branch})
                        WHERE target_base.method_name IS NULL
                        OPTIONAL MATCH (target_main {class_name: rel.target_class, project_id: rel.project_id, branch: $main_branch})
                        WHERE target_main.method_name IS NULL
                        WITH source, COALESCE(target_base, target_main) AS target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:USE]->(target)
                        """
                        all_queries.append(
                            (class_use_query, {'relationships': class_use_rels, 'base_branch': base_branch,
                                               'main_branch': main_branch}))
                    else:
                        class_use_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE source.method_name IS NULL
                        MATCH (target {class_name: rel.target_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE target.method_name IS NULL
                        MERGE (source)-[:USE]->(target)
                        """
                        all_queries.append((class_use_query, {'relationships': class_use_rels}))

                # Handle method-level USE relationships
                if method_use_rels:
                    if main_branch:
                        method_use_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                        OPTIONAL MATCH (target_base {class_name: rel.target_class, project_id: rel.project_id, branch: $base_branch})
                        WHERE target_base.method_name IS NULL
                        OPTIONAL MATCH (target_main {class_name: rel.target_class, project_id: rel.project_id, branch: $main_branch})
                        WHERE target_main.method_name IS NULL
                        WITH source, COALESCE(target_base, target_main) AS target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:USE]->(target)
                        """
                        all_queries.append(
                            (method_use_query, {'relationships': method_use_rels, 'base_branch': base_branch,
                                                'main_branch': main_branch}))
                    else:
                        method_use_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                        MATCH (target {class_name: rel.target_class, project_id: rel.project_id, branch: rel.branch})
                        WHERE target.method_name IS NULL
                        MERGE (source)-[:USE]->(target)
                        """
                    all_queries.append((method_use_query, {'relationships': method_use_rels}))

        return all_queries

    def execute_queries_batch(self, queries_with_params: List[Tuple[str, Dict]], max_retries: int = 3):
        with self.db.driver.session() as session:
            for i, (query, params) in enumerate(queries_with_params):
                retry_count = 0
                while retry_count < max_retries:
                    try:
                        result = session.run(query, params)
                        result.consume()
                        break
                    except Exception as e:
                        retry_count += 1
                        logger.error(
                            "Neo4j query failed (attempt %s/%s): %s\nQuery: %s\nParams: %s",
                            retry_count,
                            max_retries,
                            str(e),
                            query.strip(),
                            params
                        )
                        if retry_count >= max_retries:
                            raise e

    def import_code_chunks(self, chunks: List[CodeChunk], batch_size: int = 500, main_branch: Optional[str] = None,
                           base_branch: Optional[str] = None, pull_request_id: Optional[str] = None):
        self.create_indexes()
        queries_with_params = self.generate_cypher_from_chunks(chunks, batch_size, main_branch, base_branch,
                                                               pull_request_id)
        self.execute_queries_batch(queries_with_params)

