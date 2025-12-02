"""
Hướng dẫn sử dụng Branch-Aware Graph Design

File này hướng dẫn cách sử dụng các hàm đã được cập nhật để hỗ trợ branch-aware design.
"""

from source_atlas.neo4jdb.neo4j_service import Neo4jService
from source_atlas.models.domain_models import CodeChunk, Method, ChunkType

# =============================================================================
# TÌNH HUỐNG 1: Import develop branch (main branch)
# =============================================================================
print("=" * 80)
print("TÌNH HUỐNG 1: Import develop branch (main branch)")
print("=" * 80)

service = Neo4jService()

# Giả sử bạn đã parse code và có các chunks
develop_chunks = [...]  # Danh sách CodeChunk từ develop branch

# Import develop branch
service.import_code_chunks_simple(
    chunks=develop_chunks,
    batch_size=100,
    version="commit_abc123",  # Version hiện tại
    # Không cần base_branch cho main branch
)

print("✅ Đã import develop branch")
print("   - Tất cả nodes có: status='ACTIVE', version='commit_abc123'")
print("   - Tất cả relationships có: status='ACTIVE', version='commit_abc123'")

# =============================================================================
# TÌNH HUỐNG 2: Import feature branch với deleted nodes
# =============================================================================
print("\n" + "=" * 80)
print("TÌNH HUỐNG 2: Import feature/new-api branch (có thay đổi)")
print("=" " * 80)

# Feature branch parse từ code
feature_chunks = [...]  # Danh sách CodeChunk từ feature/new-api

# Danh sách các nodes đã bị xóa (so với develop)
# Bạn cần tự detect những gì bị xóa bằng cách so sánh develop vs feature
deleted_nodes = [
    {
        'class_name': 'com.example.UserService',
        'method_name': 'deleteUser',  # Method bị xóa
        'project_id': 1,
        'branch': 'feature/new-api',
        'node_type': 'MethodNode',
        'ast_hash': 'hash_old_deleteuser',
        'file_path': 'src/UserService.java'
    },
    {
        'class_name': 'com.example.LegacyService',
        'method_name': None,  # Class bị xóa
        'project_id': 1,
        'branch': 'feature/new-api',
        'node_type': 'ClassNode',
        'ast_hash': 'hash_legacy',
        'file_path': 'src/LegacyService.java'
    }
]

# Import feature branch
service.import_code_chunks_simple(
    chunks=feature_chunks,
    batch_size=100,
    main_branch="develop",
    base_branch="develop",  # Branch mà feature diverged from
    version="commit_def456",  # Current version
    base_version="commit_abc123",  # Version của develop khi tạo feature branch
    deleted_nodes=deleted_nodes  # Nodes bị xóa
)

print("✅ Đã import feature/new-api branch")
print("   - Modified nodes: status='MODIFIED' hoặc 'ACTIVE'")
print("   - Deleted nodes: status='DELETED' (tombstone nodes)")
print("   - Tất cả nodes có: base_branch='develop', base_version='commit_abc123'")

# =============================================================================
# TÌNH HUỐNG 3: Detect status cho nodes TRƯỚC KHI import
# =============================================================================
print("\n" + "=" * 80)
print("TÌNH HUỐNG 3: Tự động detect status")
print("=" * 80)

def detect_changes_and_import(service, develop_chunks, feature_chunks, project_id, branch_name):
    """
    Hàm helper để detect changes và import với đúng status
    """
    from typing import Dict, List, Set
    
    # Build map của develop nodes
    develop_map = {}
    for chunk in develop_chunks:
        develop_map[chunk.full_class_name] = chunk.ast_hash
        for method in chunk.methods:
            key = f"{chunk.full_class_name}.{method.name}"
            develop_map[key] = method.ast_hash
    
    # Build map của feature nodes
    feature_map = {}
    for chunk in feature_chunks:
        feature_map[chunk.full_class_name] = chunk.ast_hash
        for method in chunk.methods:
            key = f"{chunk.full_class_name}.{method.name}"
            feature_map[key] = method.ast_hash
    
    # Detect deleted nodes
    deleted_nodes = []
    for key, hash_val in develop_map.items():
        if key not in feature_map:
            # Node bị xóa
            if '.' in key:  # Method
                class_name, method_name = key.rsplit('.', 1)
                deleted_nodes.append({
                    'class_name': class_name,
                    'method_name': method_name,
                    'project_id': project_id,
                    'branch': branch_name,
                    'node_type': 'MethodNode',
                    'ast_hash': hash_val
                })
            else:  # Class
                deleted_nodes.append({
                    'class_name': key,
                    'method_name': None,
                    'project_id': project_id,
                    'branch': branch_name,
                    'node_type': 'ClassNode',
                    'ast_hash': hash_val
                })
    
    # Set status cho feature chunks
    for chunk in feature_chunks:
        if chunk.full_class_name in develop_map:
            if develop_map[chunk.full_class_name] != chunk.ast_hash:
                chunk.status = 'MODIFIED'  # Class bị modify
            else:
                chunk.status = 'ACTIVE'  # Class không đổi
        else:
            chunk.status = 'ACTIVE'  # Class mới
        
        # Set status cho methods
        for method in chunk.methods:
            key = f"{chunk.full_class_name}.{method.name}"
            if key in develop_map:
                if develop_map[key] != method.ast_hash:
                    method.status = 'MODIFIED'  # Method bị modify
                else:
                    method.status = 'ACTIVE'  # Method không đổi
            else:
                method.status = 'ACTIVE'  # Method mới
    
    # Import với status đã được set
    service.import_code_chunks_simple(
        chunks=feature_chunks,
        batch_size=100,
        main_branch="develop",
        base_branch="develop",
        version="current_commit",
        base_version="base_commit",
        deleted_nodes=deleted_nodes
    )
    
    return len(deleted_nodes)

# Sử dụng
develop_chunks = [...]  # Parse từ develop
feature_chunks = [...]  # Parse từ feature branch

deleted_count = detect_changes_and_import(
    service, develop_chunks, feature_chunks, 
    project_id=1, 
    branch_name="feature/new-api"
)

print(f"✅ Đã detect và import với {deleted_count} deleted nodes")

# =============================================================================
# TÌNH HUỐNG 4: Query nodes theo branch
# =============================================================================
print("\n" + "=" * 80)
print("TÌNH HUỐNG 4: Query nodes")
print("=" * 80)

# Query tất cả active nodes trong feature branch
query_active = """
MATCH (n {project_id: '1', branch: 'feature/new-api'})
WHERE n.status IN ['ACTIVE', 'MODIFIED']
RETURN n
ORDER BY n.class_name, n.method_name
"""

# Query deleted nodes (tombstones)
query_deleted = """
MATCH (n {project_id: '1', branch: 'feature/new-api', status: 'DELETED'})
RETURN n.class_name, n.method_name, n.version
"""

# Query detect conflicts giữa 2 feature branches
query_conflicts = """
MATCH (n1 {project_id: '1', branch: 'feature/first'})
WHERE n1.status IN ['MODIFIED', 'DELETED']
WITH n1.class_name AS class_name, n1.method_name AS method_name, n1
MATCH (n2 {project_id: '1', branch: 'feature/second', class_name: class_name})
WHERE n2.status IN ['MODIFIED', 'DELETED']
  AND (method_name IS NULL AND n2.method_name IS NULL 
       OR n2.method_name = method_name)
RETURN 
    class_name,
    method_name,
    n1.status AS status1,
    n2.status AS status2
"""

print("Query examples created ✅")

# =============================================================================
# KẾT LUẬN
# =============================================================================
print("\n" + "=" * 80)
print("KẾT LUẬN")
print("=" * 80)
print("""
Branch-Aware Design đã được implement thông qua việc sửa đổi các hàm hiện có:

1. ✅ generate_cypher_from_chunks() - Thêm properties: version, status, base_branch, base_version
2. ✅ import_code_chunks() - Nhận thêm parameters: version, base_version, deleted_nodes
3. ✅ import_code_chunks_simple() - Nhận thêm parameters tương tự
4. ✅ Tombstone nodes - Tự động tạo cho deleted entities

CÁC PROPERTIES MỚI:

Nodes:
- version: Commit hash hiện tại
- status: 'ACTIVE', 'MODIFIED', hoặc 'DELETED'
- base_branch: Branch mà feature diverged from
- base_version: Version của base branch

Relationships:
- version: Commit hash
- status: 'ACTIVE' hoặc 'DELETED'
- branch: Branch name

CÁCH SỬ DỤNG:

1. Main branch: Chỉ cần truyền version
2. Feature branch: Truyền version, base_branch, base_version, deleted_nodes
3. Deleted nodes: Tự detect bằng cách so sánh với base branch
4. Status: Có thể set manually hoặc để mặc định 'ACTIVE'
""")
