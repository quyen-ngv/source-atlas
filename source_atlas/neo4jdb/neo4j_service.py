from typing import List, Dict, Tuple, Optional

from loguru import logger

from source_atlas.neo4jdb.neo4j_db import Neo4jDB
from source_atlas.neo4jdb.neo4j_dto import Neo4jNodeDto, Neo4jPathDto, Neo4jTraversalResultDto
from source_atlas.models.domain_models import CodeChunk, ChunkType


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
    if not node:
        return None

    node_dict = dict(node)
    return Neo4jNodeDto(
        id=node.id,
        labels=list(node.labels),
        properties=node_dict,
        **node_dict
    )


def _path_to_dto(path) -> Optional[Neo4jPathDto]:
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
    start_node = nodes[index] if index < len(nodes) else None
    end_node = nodes[index + 1] if index + 1 < len(nodes) else None
    return start_node, end_node


def _create_relationship_data(rel, start_node, end_node):
    return {
        "type": rel.type,
        "start_node": start_node,
        "end_node": end_node,
        "properties": dict(rel)
    }


def _create_summary_item(step_index, rel, start_node, end_node):
    return {
        "step": step_index + 1,
        "from": _create_node_summary(start_node) if start_node else None,
        "relationship": rel.type,
        "to": _create_node_summary(end_node) if end_node else None
    }


def _create_node_summary(node):
    return {
        "class_name": node.class_name if node else None,
        "method_name": node.method_name if node else None,
        "node_type": node.labels[0] if node and node.labels else None
    }


class Neo4jService:
    def __init__(self, db: Neo4jDB | None = None):
        self.db = db or Neo4jDB()

    def get_nodes_by_node_specs(self, node_specs: List[Dict], project_id: int, branch: str,
                                pull_request_id: Optional[str] = None) -> List[Neo4jNodeDto]:
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
            "CREATE INDEX IF NOT EXISTS FOR (n:EndpointNode) ON (n.class_name, n.method_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:MethodNode) ON (n.class_name, n.method_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ClassNode) ON (n.class_name, n.project_id, n.branch)",
            "CREATE INDEX IF NOT EXISTS FOR (n:ConfigurationNode) ON (n.class_name, n.project_id, n.branch)",

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
                                    base_branch: Optional[str] = None, pull_request_id: Optional[str] = None,
                                    version: Optional[str] = None,
                                    base_version: Optional[str] = None,
                                    deleted_nodes: Optional[List[Dict]] = None) -> \
            List[Tuple[str, Dict]]:
        """
        Generate Cypher queries from code chunks with branch-aware support.
        
        New parameters for branch-aware design:
            version: Current commit hash/version for this import
            base_version: Base branch version when feature branch was created
            deleted_nodes: List of deleted node info (for creating tombstones)
                          Each dict should have: {'class_name': str, 'method_name': str or None, 'ast_hash': str}
        """
        all_queries = []

        # Step 1: Create tombstone nodes for deleted entities (if any)
        if deleted_nodes:
            tombstone_data = []
            for deleted in deleted_nodes:
                # Determine node type
                if deleted.get('method_name'):
                    node_type = deleted.get('node_type', 'MethodNode')
                else:
                    node_type = deleted.get('node_type', 'ClassNode')
                
                tombstone = {
                    'name': deleted['name'],
                    'node_type': node_type,
                    'class_name': deleted['class_name'],
                    'method_name': deleted.get('method_name'),
                    'file_path': deleted.get('file_path', ''),
                    'content': f"[DELETED] {deleted['class_name']}{('.' + deleted.get('method_name')) if deleted.get('method_name') else ''}",
                    'ast_hash': deleted.get('ast_hash', ''),
                    'project_id': str(deleted.get('project_id', chunks[0].project_id if chunks else '')),
                    'branch': deleted.get('branch', chunks[0].branch if chunks else ''),
                    'version': version or 'unknown',
                    'status': 'DELETED',
                    'base_branch': base_branch,
                    'base_version': base_version
                }
                tombstone_data.append(tombstone)
            
            # Create tombstone nodes
            if tombstone_data:
                tombstone_query = """
                UNWIND $tombstones AS tomb
                CALL apoc.create.node([tomb.node_type], {
                    name: tomb.name,
                    class_name: tomb.class_name,
                    method_name: tomb.method_name,
                    file_path: tomb.file_path,
                    content: tomb.content,
                    ast_hash: tomb.ast_hash,
                    project_id: tomb.project_id,
                    branch: tomb.branch,
                    version: tomb.version,
                    status: tomb.status,
                    base_branch: tomb.base_branch,
                    base_version: tomb.base_version
                }) YIELD node
                RETURN count(node) AS created_count
                """
                all_queries.append((tombstone_query, {'tombstones': tombstone_data}))
        
        # Step 2: Process regular nodes (classes and methods)
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
                
                # Determine class node status
                class_status = 'ACTIVE'
                if base_branch and base_version:
                    # For feature branches, status could be MODIFIED if ast_hash changed
                    # This would require comparing with base, but we'll default to ACTIVE
                    # Caller can pass pre-computed status if needed
                    class_status = getattr(chunk, 'status', 'ACTIVE')

                node_data_item = {
                    'name': chunk.class_name,
                    'node_type': node_type,
                    'file_path': file_path,
                    'class_name': class_name,
                    'content': content,
                    'ast_hash': chunk.ast_hash,
                    'project_id': str(chunk.project_id),
                    'branch': chunk.branch,
                    'version': version or 'unknown',
                    'status': class_status,
                    'base_branch': base_branch,
                    'base_version': base_version
                }

                # Add pull_request_id if branch is not main_branch
                if pull_request_id and chunk.branch != main_branch:
                    node_data_item['pull_request_id'] = pull_request_id

                node_data.append(node_data_item)

                for method in chunk.methods:
                    method_file_path = chunk.file_path
                    method_class_name = chunk.full_class_name
                    method_name = method.full_name
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
                    
                    # Determine method status
                    method_status = 'ACTIVE'
                    if base_branch and base_version:
                        method_status = getattr(method, 'status', 'ACTIVE')

                    method_node_data_item = {
                        'name': method.name,
                        'node_type': method_node_type,
                        'file_path': method_file_path,
                        'class_name': method_class_name,
                        'method_name': method_name,
                        'content': method_content,
                        'ast_hash': method.ast_hash,
                        'project_id': str(method.project_id),
                        'branch': method.branch,
                        'version': version or 'unknown',
                        'status': method_status,
                        'base_branch': base_branch,
                        'base_version': base_version,
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


            # Create new nodes with branch-aware properties
            if main_branch and base_branch:
                batch_query = """
                UNWIND $nodes AS node
                OPTIONAL MATCH (main_node {
                    class_name: node.class_name,
                    project_id: node.project_id,
                    branch: $main_branch,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END
                })
                
                OPTIONAL MATCH (base_node {
                    class_name: node.class_name,
                    project_id: node.project_id,
                    branch: $base_branch,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END
                })
                
                WITH node, main_node, base_node
                WHERE 
                    (base_node IS NOT NULL AND node.ast_hash <> base_node.ast_hash)
                    OR
                    (base_node IS NULL AND main_node IS NOT NULL AND node.ast_hash <> main_node.ast_hash)
                    OR
                    (base_node IS NULL AND main_node IS NULL)
                
                CALL apoc.create.node([node.node_type], {
                    name: node.name,
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content,
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    version: node.version,
                    status: node.status,
                    base_branch: node.base_branch,
                    base_version: node.base_version,
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
                    name: node.name,
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content,
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    version: node.version,
                    status: node.status,
                    base_branch: node.base_branch,
                    base_version: node.base_version,
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
                    name: node.name,
                    file_path: node.file_path,
                    class_name: node.class_name,
                    method_name: CASE WHEN node.method_name IS NOT NULL THEN node.method_name ELSE null END,
                    content: node.content, 
                    ast_hash: node.ast_hash,
                    project_id: node.project_id,
                    branch: node.branch,
                    version: node.version,
                    status: node.status,
                    base_branch: node.base_branch,
                    base_version: node.base_version,
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
                    method_name = method.full_name
                    for call in method.method_calls:
                        call_name = call.name
                        if call_name:
                            call_rels.append({
                                'source_class': chunk_class_name,
                                'source_method': method_name,
                                'target_method': call_name,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch,
                                'version': version or 'unknown',
                                'status': 'ACTIVE'
                            })
                    for inheritance in method.inheritance_info:
                        if inheritance:
                            implement_rels.append({
                                'source_method': inheritance,
                                'target_class': chunk_class_name,
                                'target_method': method_name,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch,
                                'version': version or 'unknown',
                                'status': 'ACTIVE'
                            })
                    for used_type in method.used_types:
                        if used_type:
                            use_rels.append({
                                'source_class': chunk_class_name,
                                'source_method': method_name,
                                'target_class': used_type,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch,
                                'version': version or 'unknown',
                                'status': 'ACTIVE'
                            })
                    
                    # Add USE relationships for method annotations
                    # Method C uses annotation D, E... -> C USE D, C USE E
                    if hasattr(method, 'annotations') and method.annotations:
                        for annotation in method.annotations:
                            if annotation:
                                use_rels.append({
                                    'source_class': chunk_class_name,
                                    'source_method': method_name,
                                    'target_class': annotation,
                                    'project_id': chunk_project_id,
                                    'branch': chunk_branch
                                })
                                # logger.debug(f"Added method annotation USE: {chunk_class_name}.{method_name} -> {annotation}")
                    
                    # Add USE relationships for handles_annotation (reverse: annotation node USE handler method)
                    # Method A handles annotation B -> B USE A (reverse relationship)
                    if hasattr(method, 'handles_annotation') and method.handles_annotation:
                        # Node B (annotation) USE Node A (handler method)
                        use_rels.append({
                            'source_class': method.handles_annotation,
                            'target_class': chunk_class_name,
                            'target_method': method_name,
                            'project_id': chunk_project_id,
                            'branch': chunk_branch
                        })
                        # logger.debug(f"Added handles_annotation USE (method): {method.handles_annotation} -> {chunk_class_name}.{method_name}")
                
                # Add USE relationships for class annotations
                # Class C uses annotation D, E... -> C USE D, C USE E
                if hasattr(chunk, 'annotations') and chunk.annotations:
                    for annotation in chunk.annotations:
                        if annotation:
                            use_rels.append({
                                'source_class': chunk_class_name,
                                'target_class': annotation,
                                'project_id': chunk_project_id,
                                'branch': chunk_branch
                            })
                            # logger.debug(f"Added class annotation USE: {chunk_class_name} -> {annotation}")
                
                # Add USE relationships for handles_annotation at class level (reverse: annotation node USE handler class)
                # Class A handles annotation B -> B USE A (reverse relationship)
                if hasattr(chunk, 'handles_annotation') and chunk.handles_annotation:
                    # Node B (annotation) USE Node A (handler class)
                    use_rels.append({
                        'source_class': chunk.handles_annotation,
                        'target_class': chunk_class_name,
                        'project_id': chunk_project_id,
                        'branch': chunk_branch
                    })
                    # logger.debug(f"Added handles_annotation USE (class): {chunk.handles_annotation} -> {chunk_class_name}")

            if call_rels:
                if main_branch:
                    # Use base_branch first (if provided), then fallback to main_branch
                    if base_branch:
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
                        # Only main_branch, no base_branch
                        call_query = """
                        UNWIND $relationships AS rel
                        MATCH (source {class_name: rel.source_class, method_name: rel.source_method, project_id: rel.project_id, branch: rel.branch})
                        OPTIONAL MATCH (target_main {method_name: rel.target_method, project_id: rel.project_id, branch: $main_branch})
                        WITH source, target_main AS target
                        WHERE target IS NOT NULL
                        MERGE (source)-[:CALL]->(target)
                        """
                        all_queries.append((call_query, {'relationships': call_rels, 'main_branch': main_branch}))
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

    def copy_unchanged_nodes_from_main(
            self,
            project_id: int,
            main_branch: str,
            current_branch: str,
            changed_chunks: List[CodeChunk],
            batch_size: int = 500,
            rel_batch_size: int = 500
    ):
        """
        Copy nodes from main branch to current branch,
        except for changed nodes in trong changed_chunks.
        """
        changed_node_hashes = self._build_changed_node_hashes(changed_chunks)
        params = self._build_copy_params(project_id, main_branch, current_branch, changed_node_hashes)

        logger.info(
            f"Copying unchanged nodes from '{main_branch}' to '{current_branch}' "
            f"(project_id={project_id}, skipping {len(changed_node_hashes)} changed nodes)"
        )

        try:
            with self.db.driver.session() as session:
                self._cleanup_existing_mappings(session, params, project_id)
                total_copied = self._copy_nodes_in_batches(session, params, batch_size)
                self._copy_all_relationships(session, params, rel_batch_size)
                self._remove_duplicate_nodes(session, params)
                self._cleanup_mapping_nodes(session, params)
                return total_copied
        except Exception as e:
            logger.error(f"Failed to copy unchanged nodes and relationships: {str(e)}")
            raise e


    def _build_changed_node_hashes(self, changed_chunks: List[CodeChunk]) -> dict:
        if not changed_chunks:
            logger.info("No changed chunks provided, copying all nodes from main branch")
            return {}

        changed_node_hashes = {}
        for chunk in changed_chunks:
            changed_node_hashes[chunk.full_class_name] = chunk.ast_hash
            for method in chunk.methods:
                method_key = f"{chunk.full_class_name}.{method.full_name}"
                changed_node_hashes[method_key] = method.ast_hash
        return changed_node_hashes

    def _build_copy_params(self, project_id: int, main_branch: str, current_branch: str,
                           changed_node_hashes: dict) -> dict:
        return {
            'project_id': str(project_id),
            'main_branch': main_branch,
            'current_branch': current_branch,
            'changed_node_hashes': changed_node_hashes
        }

    def _cleanup_existing_mappings(self, session, params: dict, project_id: int):
        cleanup_old_mappings = """
            MATCH (mapping:NodeMapping {project_id: $project_id, branch: $current_branch})
            DELETE mapping
            RETURN count(mapping) AS cleaned_old_mappings
            """
        cleanup_result = session.run(cleanup_old_mappings, params)
        cleanup_record = cleanup_result.single()
        cleaned_old = cleanup_record['cleaned_old_mappings'] if cleanup_record else 0
        if cleaned_old > 0:
            logger.info(f"Cleaned up {cleaned_old} old mapping nodes from previous runs")

        cleanup_orphaned = """
            MATCH (mapping:NodeMapping {project_id: $project_id})
            WHERE NOT EXISTS {
                MATCH (n {project_id: $project_id}) WHERE id(n) = mapping.old_id OR id(n) = mapping.new_id
            }
            DELETE mapping
            RETURN count(mapping) AS cleaned_orphaned
            """
        orphaned_result = session.run(cleanup_orphaned, params)
        orphaned_record = orphaned_result.single()
        cleaned_orphaned = orphaned_record['cleaned_orphaned'] if orphaned_record else 0
        if cleaned_orphaned > 0:
            logger.info(f"Cleaned up {cleaned_orphaned} orphaned mapping nodes for project {project_id}")

    def _copy_nodes_in_batches(self, session, params: dict, batch_size: int) -> int:
        count_query = """
        MATCH(main_node {project_id: $project_id, branch: $main_branch})
        WHERE main_node.pull_request_id IS NULL
        WITH main_node,
            CASE
                WHEN main_node.method_name IS NOT NULL
                THEN main_node.class_name + '.' + main_node.method_name
                ELSE main_node.class_name
            END AS node_key
        WHERE(node_key IN keys($changed_node_hashes) AND main_node.ast_hash = $changed_node_hashes[node_key])
            OR(NOT node_key IN keys($changed_node_hashes))
        RETURN count(main_node) AS total_nodes
        """

        count_result = session.run(count_query, params)
        total_nodes = count_result.single()['total_nodes']
        logger.info(f"Found {total_nodes} nodes to copy from '{params['main_branch']}' to '{params['current_branch']}'")

        total_copied = 0
        skip = 0
        while skip < total_nodes:
            batch_copy_query = self._create_batch_copy_query(skip, batch_size)
            batch_result = session.run(batch_copy_query, params)
            batch_record = batch_result.single()
            batch_copied = batch_record['copied_count'] if batch_record else 0
            total_copied += batch_copied
            skip += batch_size

            logger.info(f"Copied batch: {batch_copied} nodes (total: {total_copied}/{total_nodes})")
            if batch_copied == 0:
                break

        logger.info(
            f"Completed copying {total_copied} nodes from '{params['main_branch']}' to '{params['current_branch']}'")
        return total_copied

    def _copy_all_relationships(self, session, params: dict, rel_batch_size: int):
        self._copy_internal_relationships(session, params, rel_batch_size)
        self._copy_cross_relationships(session, params, rel_batch_size)
        self._copy_reverse_cross_relationships(session, params, rel_batch_size)

    def _copy_internal_relationships(self, session, params: dict, rel_batch_size: int):
        rel_count_query = """
        MATCH (main_source {project_id: $project_id, branch: $main_branch})-[rel]->(main_target {project_id: $project_id, branch: $main_branch})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        MATCH (source_mapping:NodeMapping {old_id: id(main_source), project_id: $project_id, branch: $current_branch})
        MATCH (target_mapping:NodeMapping {old_id: id(main_target), project_id: $project_id, branch: $current_branch})
        RETURN count(rel) AS total_rels
        """

        rel_count_result = session.run(rel_count_query, params)
        total_rels = rel_count_result.single()['total_rels']
        # logger.info(f"Found {total_rels} relationships to copy")

        total_rel_copied = 0
        rel_skip = 0
        while rel_skip < total_rels:
            batch_rel_query = self._create_batch_relationship_query(rel_skip, rel_batch_size)
            batch_rel_result = session.run(batch_rel_query, params)
            batch_rel_record = batch_rel_result.single()
            batch_rel_copied = batch_rel_record['copied_rel_count'] if batch_rel_record else 0
            total_rel_copied += batch_rel_copied
            rel_skip += rel_batch_size

            # logger.info(f"Copied batch: {batch_rel_copied} relationships (total: {total_rel_copied}/{total_rels})")
            if batch_rel_copied == 0:
                break

        # logger.info(f"Completed copying {total_rel_copied} relationships")

    def _copy_cross_relationships(self, session, params: dict, rel_batch_size: int):
        cross_count_query = """
        MATCH(main_source {project_id: $project_id, branch: $main_branch})-[rel]->(main_target {project_id: $project_id, branch: $main_branch})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        MATCH(source_mapping: NodeMapping {old_id: id(main_source), project_id: $project_id, branch: $current_branch})
        WITH main_source, main_target, rel, source_mapping
        WHERE NOT EXISTS {
            MATCH(tm: NodeMapping {old_id: id(main_target), project_id: $project_id, branch: $current_branch})
        }
        RETURN count(rel) AS total_cross_rels
        """

        cross_count_result = session.run(cross_count_query, params)
        total_cross_rels = cross_count_result.single()['total_cross_rels']
        logger.info(f"Found {total_cross_rels} cross-relationships to create")

        cross_rel_copied = 0
        cross_rel_skip = 0
        while cross_rel_skip < total_cross_rels:
            batch_cross_query = self._create_cross_relationship_query(cross_rel_skip, rel_batch_size)
            batch_cross_result = session.run(batch_cross_query, params)
            batch_cross_record = batch_cross_result.single()
            batch_cross_copied = batch_cross_record['cross_rel_count'] if batch_cross_record else 0
            cross_rel_copied += batch_cross_copied
            cross_rel_skip += rel_batch_size

            logger.info(
                f"Created batch: {batch_cross_copied} cross-relationships (total: {cross_rel_copied}/{total_cross_rels})")
            if batch_cross_copied == 0:
                break

        # logger.info(f"Completed creating {cross_rel_copied} cross-relationships from copied to changed")

    def _copy_reverse_cross_relationships(self, session, params: dict, rel_batch_size: int):
        reverse_count_query = """
        MATCH(main_source {project_id: $project_id, branch: $main_branch})-[rel]->(main_target {project_id: $project_id, branch: $main_branch})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        WITH main_source, main_target, rel
        WHERE NOT EXISTS {
            MATCH(sm: NodeMapping {old_id: id(main_source), project_id: $project_id, branch: $current_branch})
        }
        MATCH(target_mapping: NodeMapping {old_id: id(main_target), project_id: $project_id, branch: $current_branch})
        RETURN count(rel) AS total_reverse_rels
        """

        reverse_count_result = session.run(reverse_count_query, params)
        total_reverse_rels = reverse_count_result.single()['total_reverse_rels']
        logger.info(f"Found {total_reverse_rels} reverse cross-relationships to create")

        reverse_rel_copied = 0
        reverse_rel_skip = 0
        while reverse_rel_skip < total_reverse_rels:
            batch_reverse_query = self._create_reverse_cross_relationship_query(reverse_rel_skip, rel_batch_size)
            batch_reverse_result = session.run(batch_reverse_query, params)
            batch_reverse_record = batch_reverse_result.single()
            batch_reverse_copied = batch_reverse_record['reverse_rel_count'] if batch_reverse_record else 0
            reverse_rel_copied += batch_reverse_copied
            reverse_rel_skip += rel_batch_size

            logger.info(
                f"Created batch: {batch_reverse_copied} reverse cross-relationships (total: {reverse_rel_copied}/{total_reverse_rels})")
            if batch_reverse_copied == 0:
                break

        logger.info(f"Completed creating {reverse_rel_copied} cross-relationships from changed to copied")

    def _remove_duplicate_nodes(self, session, params: dict):
        duplicate_check_query = """
        MATCH(n {project_id: $project_id, branch: $current_branch})
        WHERE n.pull_request_id IS NULL
        WITH n.class_name AS class_name,
            n.method_name AS method_name,
            collect(n) AS nodes
        WHERE size(nodes) > 1
        WITH nodes[1..] AS duplicates
        UNWIND duplicates AS duplicate
        DETACH DELETE duplicate
        RETURN count(duplicate) AS removed_duplicates
        """

        dup_result = session.run(duplicate_check_query, params)
        dup_record = dup_result.single()
        removed_dups = dup_record['removed_duplicates'] if dup_record else 0
        if removed_dups > 0:
            logger.warning(f"Removed {removed_dups} duplicate nodes")

    def _cleanup_mapping_nodes(self, session, params: dict):
        cleanup_query = """
        MATCH(mapping: NodeMapping {project_id: $project_id, branch: $current_branch})
        DELETE mapping
        RETURN count(mapping) AS deleted_mappings
        """

        try:
            cleanup_result = session.run(cleanup_query, params)
            cleanup_record = cleanup_result.single()
            deleted_mappings = cleanup_record['deleted_mappings'] if cleanup_record else 0
            logger.info(f"Cleaned up {deleted_mappings} temporary mapping nodes")
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup mapping nodes: {str(cleanup_error)}")

    def _create_batch_copy_query(self, skip_count: int, limit_count: int) -> str:
        return f""" 
        MATCH(main_node {{project_id: $project_id, branch: $main_branch}})
        WHERE main_node.pull_request_id IS NULL
        WITH main_node,
            CASE
                WHEN main_node.method_name IS NOT NULL
                THEN main_node.class_name + '.' + main_node.method_name
                ELSE main_node.class_name
            END AS node_key
        WHERE(node_key IN keys($changed_node_hashes) AND main_node.ast_hash = $changed_node_hashes[node_key])
            OR(NOT node_key IN keys($changed_node_hashes))
        WITH main_node
        SKIP {skip_count}
        LIMIT {limit_count}
        WITH main_node, labels(main_node) AS node_labels
        CALL
            apoc.create.node(
                node_labels,
                main_node {{
                    . *,
                    branch: $current_branch
                }}
        ) YIELD node AS copied_node
        WITH main_node, copied_node
        MERGE(mapping: NodeMapping {{
            old_id: id(main_node),
            new_id: id(copied_node),
            project_id: $project_id,
            branch: $current_branch
        }})
        RETURN count(copied_node) AS copied_count
        """

    def _create_batch_relationship_query(self, skip_count: int, limit_count: int) -> str:
        return f"""
        MATCH(main_source
        {{project_id: $project_id, branch: $main_branch}})-[rel]->(main_target {{project_id: $project_id, branch: $main_branch}})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        MATCH(source_mapping: NodeMapping {{old_id: id(main_source), project_id: $project_id, branch: $current_branch}})
        MATCH(target_mapping: NodeMapping {{old_id: id(main_target), project_id: $project_id, branch: $current_branch}})
        WITH main_source, main_target, rel, source_mapping, target_mapping
        SKIP {skip_count}
        LIMIT {limit_count}
        MATCH(copied_source) WHERE id(copied_source) = source_mapping.new_id
        MATCH(copied_target) WHERE id(copied_target) = target_mapping.new_id
        WITH copied_source, copied_target, rel
        CALL
            apoc.create.relationship(
                copied_source,
                type(rel),
                properties(rel),
                copied_target
            )
        YIELD rel AS copied_rel
        RETURN count(copied_rel) AS copied_rel_count
        """

    def _create_cross_relationship_query(self, skip_count: int, limit_count: int) -> str:
        return f"""
        MATCH(main_source {{project_id: $project_id, branch: $main_branch}})-[rel]->(main_target {{project_id: $project_id, branch: $main_branch}})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        MATCH(source_mapping: NodeMapping {{old_id: id(main_source), project_id: $project_id, branch: $current_branch}})
        WITH main_source, main_target, rel, source_mapping
        WHERE NOT EXISTS {{
            MATCH(tm: NodeMapping {{old_id: id(main_target), project_id: $project_id, branch: $current_branch}})
        }}
        WITH main_source, main_target, rel, source_mapping
        SKIP {skip_count}
        LIMIT {limit_count}
        MATCH(copied_source) WHERE id(copied_source) = source_mapping.new_id
        MATCH(changed_target {{
            project_id: $project_id,
            branch: $current_branch,
            class_name: main_target.class_name
        }})
        WHERE(main_target.method_name IS NULL AND changed_target.method_name IS NULL)
        OR(main_target.method_name IS NOT NULL AND changed_target.method_name = main_target.method_name)
        CALL
        apoc.create.relationship(
            copied_source,
            type(rel),
            properties(rel),
            changed_target
        )
        YIELD rel AS cross_rel
        RETURN count(cross_rel) AS cross_rel_count
        """

    def _create_reverse_cross_relationship_query(self, skip_count: int, limit_count: int) -> str:
        return f"""
        MATCH(main_source
        {{project_id: $project_id, branch: $main_branch}})-[rel]->(main_target {{project_id: $project_id, branch: $main_branch}})
        WHERE main_source.pull_request_id IS NULL AND main_target.pull_request_id IS NULL
        WITH main_source, main_target, rel 
        WHERE NOT EXISTS {{
            MATCH(sm: NodeMapping {{old_id: id(main_source), project_id: $project_id, branch: $current_branch}})
        }}
        MATCH(target_mapping: NodeMapping {{old_id: id(main_target), project_id: $project_id, branch: $current_branch}})
        WITH main_source, main_target, rel, target_mapping
        SKIP {skip_count}
        LIMIT {limit_count}
        MATCH(changed_source {{
            project_id: $project_id,
            branch: $current_branch,
            class_name: main_source.class_name
        }})
        WHERE(main_source.method_name IS NULL AND changed_source.method_name IS NULL)
        OR(main_source.method_name IS NOT NULL AND changed_source.method_name = main_source.method_name)
        MATCH(copied_target) WHERE id(copied_target) = target_mapping.new_id
        CALL
            apoc.create.relationship(
                changed_source,
                type(rel),
                properties(rel),
                copied_target
            )
        YIELD rel AS reverse_rel
        RETURN count(reverse_rel) AS reverse_rel_count
        """

    def delete_branch_nodes(self, project_id: int, branch_name: str, pull_request_id: str = None):

        if pull_request_id:
            # Delete nodes with specific pull_request_id
            delete_query = """
            MATCH(n {project_id: $project_id, branch: $branch_name, pull_request_id: $pull_request_id})
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            params = {
                'project_id': str(project_id),
                'branch_name': branch_name,
                'pull_request_id': pull_request_id
            }
        else:
            # Delete ALL nodes for this branch (regardless of pull_request_id)
            delete_query = """
            MATCH(n {project_id: $project_id, branch: $branch_name})
            DETACH DELETE n
            RETURN count(n) as deleted_count
            """
            params = {
                'project_id': str(project_id),
                'branch_name': branch_name
            }

        try:
            with self.db.driver.session() as session:
                result = session.run(delete_query, params)
                record = result.single()
                deleted_count = record['deleted_count'] if record else 0
                logger.info(
                    f"Deleted {deleted_count} nodes for branch '{branch_name}' "
                    f"in project {project_id} "
                    f"(pull_request_id: {pull_request_id or 'ALL'})"
                )
                return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete branch nodes: {str(e)}")
        raise e

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
                        if retry_count >= max_retries:
                            raise e

    def import_code_chunks(self, chunks: List[CodeChunk], batch_size: int = 500, main_branch: Optional[str] = None,
                           base_branch: Optional[str] = None, pull_request_id: Optional[str] = None,
                           version: Optional[str] = None, base_version: Optional[str] = None,
                           deleted_nodes: Optional[List[Dict]] = None):
        """
        Import code chunks with relationship preservation and branch-aware support.
        
        This method ensures that relationships between unchanged nodes and changed nodes
        are preserved during the update process by:
        1. Saving relationships from unchanged → changed nodes before deletion
        2. Deleting old nodes and creating new nodes (with branch-aware properties)
        3. Restoring relationships from unchanged → new changed nodes
        4. Creating new relationships from chunk data
        5. Cleaning up duplicate relationships
        
        Args:
            chunks: List of code chunks to import
            batch_size: Batch size for processing
            main_branch: Main branch name for comparison
            base_branch: Base branch name for comparison (takes priority over main_branch)
            pull_request_id: Pull request ID if importing for a PR
            version: Current version/commit hash for this import
            base_version: Base version when feature branch was created
            deleted_nodes: List of deleted node info (for tombstone creation)
        """
        if not chunks:
            logger.warning("No chunks to import")
            return
        
        self.create_indexes()
        
        # Get project_id and branch from first chunk (all chunks should have same project_id and branch)
        project_id = chunks[0].project_id
        branch = chunks[0].branch
        
        # Default base_branch to current branch if not provided
        # This ensures relationship queries always have valid branch parameters
        if base_branch is None:
            base_branch = branch
        
        # Step 1: Save relationships from unchanged → changed nodes before deletion
        logger.info(f"Step 1/5: Saving relationships from unchanged to changed nodes...")
        saved_rels = self.save_changed_nodes_relationships(
            project_id=project_id,
            branch=branch,
            changed_chunks=chunks
        )
        logger.info(f"Saved {len(saved_rels)} relationships from unchanged to changed nodes")
        
        # Step 2 & 3: Delete old nodes and create new nodes (combined in generate_cypher_from_chunks)
        logger.info(f"Step 2/5: Importing changed nodes only...")
        self.import_changed_chunk_nodes_only(
            chunks=chunks,
            main_branch=main_branch,
            base_branch=base_branch,
            batch_size=batch_size,
            pull_request_id=pull_request_id,
            version=version,
            base_version=base_version,
            deleted_nodes=deleted_nodes
        )
        
        # Step 4: Restore relationships from unchanged → new changed nodes
        if saved_rels:
            logger.info(f"Step 3/5: Restoring relationships from unchanged to new changed nodes...")
            self.restore_changed_nodes_relationships(
                project_id=project_id,
                branch=branch,
                saved_relationships=saved_rels,
                changed_chunks=chunks
            )
        else:
            logger.info(f"Step 3/5: No relationships to restore")
        
        # Step 5: Create relationships from chunk data (changed → unchanged, changed → changed)
        logger.info(f"Step 4/5: Creating relationships from chunk data...")
        self.import_changed_chunk_relationships(
            chunks=chunks,
            current_branch=branch,
            main_branch=main_branch,
            base_branch=base_branch,
            batch_size=batch_size,
            version=version
        )
        
        # Step 6: Clean up duplicate relationships
        logger.info(f"Step 5/5: Cleaning up duplicate relationships...")
        self.remove_duplicate_relationships(
            project_id=project_id,
            branch=branch
        )
        
        logger.info(f"✅ Successfully imported {len(chunks)} changed chunks with relationship preservation")

    def import_code_chunks_simple(self, chunks: List[CodeChunk], batch_size: int = 500, 
                                  main_branch: Optional[str] = None,
                                  base_branch: Optional[str] = None, 
                                  pull_request_id: Optional[str] = None,
                                  version: Optional[str] = None,
                                  base_version: Optional[str] = None,
                                  deleted_nodes: Optional[List[Dict]] = None):
        """
        Simple import without relationship preservation, with branch-aware support.
        
        Use this method for:
        - Initial import of a new branch
        - Full rebuild of the graph
        - Cases where you don't need to preserve relationships between unchanged and changed nodes
        
        For incremental updates where relationship preservation is important, use import_code_chunks() instead.
        
        Args:
            chunks: List of code chunks to import
            batch_size: Batch size for processing
            main_branch: Main branch name for comparison
            base_branch: Base branch name for comparison (takes priority over main_branch)
            pull_request_id: Pull request ID if importing for a PR
            version: Current version/commit hash for this import
            base_version: Base version when feature branch was created
            deleted_nodes: List of deleted node info (for tombstone creation)
        """
        if not chunks:
            logger.warning("No chunks to import")
            return
            
        self.create_indexes()
        queries_with_params = self.generate_cypher_from_chunks(
            chunks, batch_size, main_branch, base_branch, pull_request_id,
            version=version, base_version=base_version, deleted_nodes=deleted_nodes
        )
        self.execute_queries_batch(queries_with_params)
        logger.info(f"✅ Imported {len(chunks)} chunks (simple mode)")


    def import_changed_chunk_nodes_only(self, chunks: List[CodeChunk], main_branch: str, base_branch: str = None,
                                        batch_size: int = 500, pull_request_id: str = None,
                                        version: str = None, base_version: str = None,
                                        deleted_nodes: List[Dict] = None):

        self.create_indexes()

        # Generate queries with base_branch and main_branch comparison to filter by ast_hash
        queries_with_params = self.generate_cypher_from_chunks(
            chunks,
            batch_size,
            main_branch=main_branch,  # Pass main_branch for ast_hash comparison
            base_branch=base_branch,  # Pass base_branch for ast_hash comparison (priority)
            pull_request_id=pull_request_id,
            version=version,  # Pass version for branch-aware nodes
            base_version=base_version,
            deleted_nodes=deleted_nodes  # Pass deleted nodes for tombstone creation
        )

        # Filter to only include node creation queries (not relationship queries)
        node_queries = []
        for query, params in queries_with_params:
            # Skip relationship queries (they contain MERGE with relationship patterns)
            if '-[' not in query and 'MERGE (source)-[' not in query:
                node_queries.append((query, params))

        self.execute_queries_batch(node_queries)
        logger.info(
            f"Imported changed chunk nodes with different ast_hash from main branch (relationships will be created later)")

    def import_changed_chunk_relationships(self, chunks: List[CodeChunk], current_branch: str, main_branch: str = None,
                                           base_branch: str = None, batch_size: int = 500, version: str = None):

        queries_with_params = self.generate_cypher_from_chunks(
            chunks,
            batch_size,
            main_branch=main_branch,
            base_branch=base_branch,
            pull_request_id=None,
            version=version  # Pass version for branch-aware relationships
        )

        # Filter to only include relationship queries
        relationship_queries = []
        for query, params in queries_with_params:
            # Only include relationship queries (they contain MERGE with relationship patterns or relationship keywords)
            if any(keyword in query for keyword in
                   ['MERGE (source)-[', 'MERGE (target)-[', ']->(target)', 'CALL]', 'IMPLEMENT]', 'USE]', 'EXTEND]']):
                relationship_queries.append((query, params))

        self.execute_queries_batch(relationship_queries)
        logger.info(f"Imported relationships for {len(chunks)} changed chunks")

    def get_related_nodes(
            self,
            target_nodes: List[Neo4jNodeDto],
            max_level: int = 20,
            min_level: int = 1,
            relationship_filter: str = "CALL>|<IMPLEMENT|<EXTEND|USE>|<BRANCH"
    ) -> List[Neo4jTraversalResultDto]:
        query = """
        WITH $targets AS targets
        MATCH (endpoint)
        WHERE endpoint.project_id = $targets[0].project_id
        AND any(t IN targets WHERE
          t.class_name = endpoint.class_name AND
          t.branch = endpoint.branch AND
          (
            (t.method_name IS NULL AND endpoint.method_name IS NULL)
            OR (t.method_name = endpoint.method_name)
          )
        )
        CALL apoc.path.expandConfig(endpoint, {
          relationshipFilter: "CALL>|<IMPLEMENT|<EXTEND|USE>|<BRANCH",
          minLevel: $min_level,
          maxLevel: $max_level,
          bfs: true,
          uniqueness: "NODE_GLOBAL",
          filterStartNode: false
        }) YIELD path
        WITH endpoint, path,
             nodes(path) AS node_list,
             relationships(path) AS rel_list
        WITH endpoint, path, node_list, rel_list, 
            [i IN range(0, size(rel_list) - 1) |
            CASE 
                WHEN type(rel_list[i]) = 'BRANCH'
                    AND node_list[i + 1].branch = 'develop'
                    AND node_list[i].branch = 'main'
                THEN node_list[i+1]
                ELSE null
            END
            ] AS exclude_nodes
        WITH endpoint, path, node_list, rel_list, exclude_nodes,
             [i IN range(0, size(rel_list)-1) |
                CASE
                  WHEN type(rel_list[i]) = 'CALL'
                       AND node_list[i+1].method_name IS NOT NULL
                  THEN node_list[i+1]

                  WHEN type(rel_list[i]) IN ['IMPLEMENT', 'EXTEND', 'BRANCH']
                  THEN node_list[i+1]

                  WHEN type(rel_list[i]) = 'USE'
                       AND node_list[i+1].method_name IS NULL
                  THEN node_list[i+1]
                  ELSE null
                END
             ] AS filtered_nodes
        RETURN endpoint, path,
               [node IN filtered_nodes WHERE node IS NOT NULL AND NOT node IN exclude_nodes] AS visited_nodes
        ORDER BY path
        """

        params = {
            'targets': [node.model_dump() for node in target_nodes],
            'relationship_filter': relationship_filter,
            'min_level': min_level,
            'max_level': max_level
        }

        with self.db.driver.session() as session:
            result = session.run(query, params)
            return [
                Neo4jTraversalResultDto(
                    endpoint=_node_to_dto(record['endpoint']),
                    path=_path_to_dto(record['path']),
                    visited_nodes=[_node_to_dto(node) for node in record['visited_nodes']]
                )
                for record in result
            ]

    def get_left_target_nodes(
            self,
            target_nodes: List[Neo4jNodeDto],
            max_level: int = 20,
            min_level: int = 1  # at least one relation with other nodes
    ) -> List[Neo4jTraversalResultDto]:

        query = """
        WITH $targets AS targets

        MATCH (endpoint)
        WHERE endpoint.project_id = $targets[0].project_id
        AND any(t IN targets WHERE
          t.class_name = endpoint.class_name AND
          (
            (t.method_name IS NULL AND endpoint.method_name IS NULL)
            OR (t.method_name = endpoint.method_name)
          )
        )

        CALL apoc.path.expandConfig(endpoint, {
          relationshipFilter: '<CALL|IMPLEMENT>|EXTEND>|<USE',
          minLevel: $min_level,
          maxLevel: $max_level,
          bfs: true,
          uniqueness: "NODE_GLOBAL",
          filterStartNode: false
        }) YIELD path

        WITH endpoint, path,
             nodes(path) AS node_list,
             relationships(path) AS rel_list

        WITH endpoint, path, node_list, rel_list,
             [i IN range(0, size(rel_list)-1) |
                CASE
                  WHEN type(rel_list[i]) = 'CALL'
                       AND node_list[i+1].method_name IS NOT NULL
                  THEN node_list[i+1]

                  WHEN type(rel_list[i]) IN ['IMPLEMENT', 'EXTEND']
                  THEN node_list[i+1]

                  WHEN type(rel_list[i]) = 'USE'
                       AND node_list[i+1].method_name IS NULL
                  THEN node_list[i+1]
                  ELSE null
                END
             ] AS filtered_nodes

        RETURN endpoint, path,
               [node IN filtered_nodes WHERE node IS NOT NULL] AS visited_nodes
        ORDER BY path
        """

        params = {
            'targets': [node.model_dump() for node in target_nodes],
            'min_level': min_level,
            'max_level': max_level
        }

        with self.db.driver.session() as session:
            result = session.run(query, params)
            return [
                Neo4jTraversalResultDto(
                    endpoint=_node_to_dto(record['endpoint']),
                    path=_path_to_dto(record['path']),
                    visited_nodes=[_node_to_dto(node) for node in record['visited_nodes']]
                )
                for record in result
            ]
    def get_nodes_by_condition(
            self,
            project_id: int,
            branch: str,
            pull_request_id: str = None,
            class_name: str = None,
            method_name: str = None
    ) -> List[Neo4jNodeDto]:
        properties = {
            'project_id': str(project_id),
            'branch': branch
        }

        if pull_request_id is not None:
            properties['pull_request_id'] = pull_request_id

        if class_name is not None:
            properties['class_name'] = class_name

        if method_name is not None:
            properties['method_name'] = method_name

        # Build property string for query
        property_pairs = [f"{key}: '{value}'" for key, value in properties.items()]
        property_string = ', '.join(property_pairs)

        query = f"MATCH (n {{{property_string}}}) RETURN n"

        try:
            with self.db.driver.session() as session:
                result = session.run(query)
                nodes = [_node_to_dto(record['n']) for record in result]
                # logger.info(f"Retrieved {len(nodes)} nodes with query: {query}")
                return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes by condition: {str(e)}", exc_info=True)
        raise

    def get_config_nodes(self, project_id: int, branch: str) -> List[Neo4jNodeDto]:
        """Get all configuration nodes for a project and branch"""
        query = """
            MATCH (n:ConfigurationNode {project_id: $project_id, branch: $branch})
            RETURN n
            ORDER BY n.class_name, n.method_name
            """

        try:
            with self.db.driver.session() as session:
                result = session.run(query, {
                    'project_id': str(project_id),
                    'branch': branch
                })
                nodes = [_node_to_dto(record['n']) for record in result]
                # logger.info(f"Retrieved {len(nodes)} config nodes for project {project_id}, branch {branch}")
                return nodes
        except Exception as e:
            logger.error(f"Failed to get config nodes: {str(e)}")
            return []

    def save_changed_nodes_relationships(self, project_id: int, branch: str, changed_chunks: List[CodeChunk]) -> List[
        Dict]:
        """Save relationships between unchanged nodes and changed nodes before deletion"""
        changed_node_keys = set()
        for chunk in changed_chunks:
            changed_node_keys.add(chunk.full_class_name)
            for method in chunk.methods:
                changed_node_keys.add(f"{chunk.full_class_name}.{method.full_name}")

        query = """
        MATCH (unchanged {project_id: $project_id, branch: $branch})-[r]->(changed {project_id: $project_id, branch: $branch})
        WHERE unchanged.pull_request_id IS NULL AND changed.pull_request_id IS NULL
        WITH unchanged, r, changed,
             CASE WHEN changed.method_name IS NOT NULL 
                  THEN changed.class_name + '.' + changed.method_name 
                  ELSE changed.class_name END AS changed_key
        WHERE changed_key IN $changed_keys
        WITH unchanged, r, changed,
             CASE WHEN unchanged.method_name IS NOT NULL 
                  THEN unchanged.class_name + '.' + unchanged.method_name 
                  ELSE unchanged.class_name END AS unchanged_key
        WHERE NOT unchanged_key IN $changed_keys
        RETURN 
            unchanged.class_name AS unchanged_class,
            unchanged.method_name AS unchanged_method,
            type(r) AS rel_type,
            changed.class_name AS changed_class,
            changed.method_name AS changed_method
        """

        with self.db.driver.session() as session:
            result = session.run(query, {
                'project_id': str(project_id),
                'branch': branch,
                'changed_keys': list(changed_node_keys)
            })
            return [dict(record) for record in result]

    def restore_changed_nodes_relationships(self, project_id: int, branch: str, saved_relationships: List[Dict],
                                            changed_chunks: List[CodeChunk]):
        """Restore relationships between unchanged nodes and newly created changed nodes"""
        if not saved_relationships:
            return

        query = """
        UNWIND $rels AS rel
        MATCH (unchanged {project_id: $project_id, branch: $branch, class_name: rel.unchanged_class})
        WHERE unchanged.pull_request_id IS NULL
          AND (rel.unchanged_method IS NULL AND unchanged.method_name IS NULL 
               OR unchanged.method_name = rel.unchanged_method)
        MATCH (changed {project_id: $project_id, branch: $branch, class_name: rel.changed_class})
        WHERE changed.pull_request_id IS NULL
          AND (rel.changed_method IS NULL AND changed.method_name IS NULL 
               OR changed.method_name = rel.changed_method)
        CALL apoc.create.relationship(unchanged, rel.rel_type, {}, changed) YIELD rel AS created_rel
        RETURN count(created_rel) AS restored_count
        """

        with self.db.driver.session() as session:
            result = session.run(query, {
                'project_id': str(project_id),
                'branch': branch,
                'rels': saved_relationships
            })
            record = result.single()
            restored = record['restored_count'] if record else 0
            logger.info(f"Restored {restored} relationships")

    def remove_duplicate_relationships(self, project_id: int, branch: str):
        """Remove duplicate relationships for a branch"""
        query = """
        MATCH (a {project_id: $project_id, branch: $branch})-[r]->(b {project_id: $project_id, branch: $branch})
        WITH a, b, type(r) AS rel_type, collect(r) AS rels
        WHERE size(rels) > 1
        FOREACH (rel IN rels[1..] | DELETE rel)
        RETURN count(rels[1..]) AS removed_count
        """

        with self.db.driver.session() as session:
            result = session.run(query, {
                'project_id': str(project_id),
                'branch': branch
            })
            record = result.single()
            removed = record['removed_count'] if record else 0
            if removed > 0:
                logger.info(f"Removed {removed} duplicate relationships")
