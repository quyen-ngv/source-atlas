"""
Test cases for Neo4j Service relationship preservation feature.

This module demonstrates how the relationship preservation works and validates
that relationships are correctly maintained when updating code chunks.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from typing import List
from source_atlas.neo4jdb.neo4j_service import Neo4jService
from source_atlas.models.domain_models import CodeChunk, ChunkType, Method, MethodCall


class TestRelationshipPreservation:
    """Test relationship preservation during code chunk updates."""
    
    @pytest.fixture
    def neo4j_service(self):
        """Create a Neo4j service instance."""
        from source_atlas.neo4jdb.neo4j_db import Neo4jDB
        
        # Create Neo4jDB with test credentials
        db = Neo4jDB(
            url="bolt://localhost:7687",
            user="neo4j",
            password="your_password"
        )
        service = Neo4jService(db=db)
        
        yield service
        
        # Teardown: close the driver
        db.close()
    
    @pytest.fixture
    def sample_chunks_v1(self) -> List[CodeChunk]:
        """
        Create sample chunks for version 1.
        
        Structure:
        - ClassA.methodA() -> calls ClassB.methodB()
        - ClassB.methodB() -> uses ClassC
        - ClassC (unchanged)
        """
        # ClassA with methodA
        method_a = Method(
            name="methodA",
            body="public void methodA() { serviceB.methodB(); }",
            ast_hash="hash_method_a_v1",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            method_calls=(MethodCall(name="methodB", params=[]),),
            used_types=(),
            inheritance_info=(),
            field_access=(),
            endpoint=()
        )
        
        chunk_a = CodeChunk(
            package="com.example",
            class_name="ClassA",
            full_class_name="ClassA",
            file_path="src/ClassA.java",
            content="class ClassA { public void methodA() { serviceB.methodB(); } }",
            ast_hash="hash_class_a_v1",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[method_a],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False
        )
        
        # ClassB with methodB (will be changed)
        method_b = Method(
            name="methodB",
            body="public void methodB() { ClassC c = new ClassC(); }",
            ast_hash="hash_method_b_v1",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            method_calls=(),
            used_types=("ClassC",),
            inheritance_info=(),
            field_access=(),
            endpoint=()
        )
        
        chunk_b = CodeChunk(
            package="com.example",
            class_name="ClassB",
            full_class_name="ClassB",
            file_path="src/ClassB.java",
            content="class ClassB { public void methodB() { ClassC c = new ClassC(); } }",
            ast_hash="hash_class_b_v1",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[method_b],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False
        )
        
        # ClassC (unchanged)
        chunk_c = CodeChunk(
            package="com.example",
            class_name="ClassC",
            full_class_name="ClassC",
            file_path="src/ClassC.java",
            content="class ClassC { }",
            ast_hash="hash_class_c_v1",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False
        )
        
        return [chunk_a, chunk_b, chunk_c]
    
    @pytest.fixture
    def sample_chunks_v2(self) -> List[CodeChunk]:
        """
        Create sample chunks for version 2 (only ClassB changed).
        
        Changes:
        - ClassB.methodB() has new implementation (different ast_hash)
        - ClassA and ClassC remain unchanged
        """
        # ClassB with methodB (CHANGED - new implementation)
        method_b = Method(
            name="methodB",
            body="public void methodB() { ClassC c = new ClassC(); c.doSomething(); }",  # Added c.doSomething()
            ast_hash="hash_method_b_v2",  # Different hash!
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            method_calls=(),
            used_types=("ClassC",),
            inheritance_info=(),
            field_access=(),
            endpoint=()
        )
        
        chunk_b = CodeChunk(
            package="com.example",
            class_name="ClassB",
            full_class_name="ClassB",
            file_path="src/ClassB.java",
            content="class ClassB { public void methodB() { ClassC c = new ClassC(); c.doSomething(); } }",
            ast_hash="hash_class_b_v2",  # Different hash!
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[method_b],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False
        )
        
        return [chunk_b]  # Only changed chunk
    
    def test_initial_import(self, neo4j_service, sample_chunks_v1):
        """
        Test initial import of all chunks.
        
        Expected:
        - All nodes created
        - All relationships created:
          * ClassA.methodA --CALL--> ClassB.methodB
          * ClassB.methodB --USE--> ClassC
        """
        # Clean up first
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
        
        # Initial import (use simple mode)
        neo4j_service.import_code_chunks_simple(
            chunks=sample_chunks_v1,
            batch_size=100
        )
        
        # Verify nodes exist
        nodes = neo4j_service.get_nodes_by_condition(
            project_id=1,
            branch="develop"
        )
        
        assert len(nodes) >= 5  # 3 classes + 2 methods
        
        # Verify relationships exist
        # Query: ClassA.methodA --CALL--> ClassB.methodB
        query = """
        MATCH (a:MethodNode {class_name: 'ClassA', method_name: 'methodA', 
                              project_id: '1', branch: 'develop'})
              -[:CALL]->
              (b:MethodNode {class_name: 'ClassB', method_name: 'methodB', 
                              project_id: '1', branch: 'develop'})
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "ClassA.methodA should call ClassB.methodB"
    
    def test_incremental_update_with_preservation(self, neo4j_service, sample_chunks_v1, sample_chunks_v2):
        """
        Test incremental update with relationship preservation.
        
        Scenario:
        1. Import v1 (all chunks)
        2. Update only ClassB (v2)
        3. Verify relationship ClassA.methodA --CALL--> ClassB.methodB is preserved
        
        Expected:
        - ClassB node is deleted and recreated with new ast_hash
        - Relationship ClassA.methodA --CALL--> ClassB.methodB is PRESERVED
        - Relationship ClassB.methodB --USE--> ClassC is recreated
        """
        # Step 1: Initial import
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
        neo4j_service.import_code_chunks_simple(chunks=sample_chunks_v1)
        
        # Step 2: Update ClassB with relationship preservation
        neo4j_service.import_code_chunks(
            chunks=sample_chunks_v2,
            main_branch="main",
            base_branch="develop",
            batch_size=100
        )
        
        # Step 3: Verify relationship is preserved
        query = """
        MATCH (a:MethodNode {class_name: 'ClassA', method_name: 'methodA', 
                              project_id: '1', branch: 'develop'})
              -[:CALL]->
              (b:MethodNode {class_name: 'ClassB', method_name: 'methodB', 
                              project_id: '1', branch: 'develop'})
        RETURN count(*) as rel_count, b.ast_hash as new_hash
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            
            # Verify relationship exists
            assert record['rel_count'] == 1, "Relationship should be preserved after update"
            
            # Verify ClassB has new ast_hash
            assert record['new_hash'] == "hash_method_b_v2", "ClassB should have new ast_hash"

        # Step 4: Verify outgoing relationship (ClassB -> ClassC) is recreated
        query_outgoing = """
        MATCH (b:MethodNode {class_name: 'ClassB', method_name: 'methodB', 
                              project_id: '1', branch: 'develop'})
              -[:USE]->
              (c:ClassNode {class_name: 'ClassC', 
                             project_id: '1', branch: 'develop'})
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query_outgoing)
            record = result.single()
            assert record['rel_count'] == 1, "Relationship ClassB -> ClassC should be recreated"
    
    def test_incremental_update_without_preservation(self, neo4j_service, sample_chunks_v1, sample_chunks_v2):
        """
        Test incremental update WITHOUT relationship preservation (using simple mode).
        
        This demonstrates the problem when not using relationship preservation.
        
        Expected:
        - ClassB node is deleted and recreated
        - Relationship ClassA.methodA --CALL--> ClassB.methodB is LOST
        """
        # Step 1: Initial import
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
        neo4j_service.import_code_chunks_simple(chunks=sample_chunks_v1)
        
        # Step 2: Update ClassB WITHOUT relationship preservation (wrong!)
        neo4j_service.import_code_chunks_simple(chunks=sample_chunks_v2)
        
        # Step 3: Verify relationship is LOST
        query = """
        MATCH (a:MethodNode {class_name: 'ClassA', method_name: 'methodA', 
                              project_id: '1', branch: 'develop'})
              -[:CALL]->
              (b:MethodNode {class_name: 'ClassB', method_name: 'methodB', 
                              project_id: '1', branch: 'develop'})
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            
            # Relationship is LOST because we didn't use preservation
            # This test demonstrates the problem!
            assert record['rel_count'] == 0, "Relationship is lost without preservation (expected behavior for this test)"
    
    def test_save_and_restore_relationships(self, neo4j_service, sample_chunks_v1, sample_chunks_v2):
        """
        Test the save and restore relationship methods directly.
        
        This is a lower-level test to verify the helper methods work correctly.
        """
        # Step 1: Initial import
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
        neo4j_service.import_code_chunks_simple(chunks=sample_chunks_v1)
        
        # Step 2: Save relationships before deletion
        saved_rels = neo4j_service.save_changed_nodes_relationships(
            project_id=1,
            branch="develop",
            changed_chunks=sample_chunks_v2
        )
        
        # Verify we saved the relationship ClassA.methodA -> ClassB.methodB
        assert len(saved_rels) > 0, "Should have saved at least one relationship"
        
        # Find the specific relationship
        call_rel = next(
            (r for r in saved_rels 
             if r['unchanged_class'] == 'ClassA' 
             and r['unchanged_method'] == 'methodA'
             and r['changed_class'] == 'ClassB'
             and r['changed_method'] == 'methodB'
             and r['rel_type'] == 'CALL'),
            None
        )
        
        assert call_rel is not None, "Should have saved ClassA.methodA --CALL--> ClassB.methodB"
        
        # Step 3: Delete and recreate ClassB
        neo4j_service.import_changed_chunk_nodes_only(
            chunks=sample_chunks_v2,
            main_branch="main",
            base_branch="develop"
        )
        
        # Step 4: Restore relationships
        neo4j_service.restore_changed_nodes_relationships(
            project_id=1,
            branch="develop",
            saved_relationships=saved_rels,
            changed_chunks=sample_chunks_v2
        )
        
        # Step 5: Verify relationship is restored
        query = """
        MATCH (a:MethodNode {class_name: 'ClassA', method_name: 'methodA'})
              -[:CALL]->
              (b:MethodNode {class_name: 'ClassB', method_name: 'methodB'})
        WHERE a.project_id = '1' AND a.branch = 'develop'
          AND b.project_id = '1' AND b.branch = 'develop'
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "Relationship should be restored"
    
    def test_remove_duplicate_relationships(self, neo4j_service):
        """
        Test that duplicate relationships are correctly removed.
        """
        # Create a simple scenario with duplicate relationships
        query = """
        // Create nodes
        CREATE (a:MethodNode {class_name: 'A', method_name: 'methodA', project_id: '1', branch: 'test'})
        CREATE (b:MethodNode {class_name: 'B', method_name: 'methodB', project_id: '1', branch: 'test'})
        
        // Create duplicate CALL relationships
        CREATE (a)-[:CALL]->(b)
        CREATE (a)-[:CALL]->(b)
        CREATE (a)-[:CALL]->(b)
        
        RETURN count(*) as created
        """
        
        with neo4j_service.db.driver.session() as session:
            session.run(query)
        
        # Remove duplicates
        neo4j_service.remove_duplicate_relationships(project_id=1, branch="test")
        
        # Verify only one relationship remains
        verify_query = """
        MATCH (a:MethodNode {class_name: 'A', method_name: 'methodA', project_id: '1', branch: 'test'})
              -[r:CALL]->
              (b:MethodNode {class_name: 'B', method_name: 'methodB', project_id: '1', branch: 'test'})
        RETURN count(r) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(verify_query)
            record = result.single()
            assert record['rel_count'] == 1, "Should have only one relationship after deduplication"
        
        # Cleanup
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="test")


class TestRelationshipPreservationEdgeCases:
    """Test edge cases for relationship preservation."""
    
    @pytest.fixture
    def neo4j_service(self):
        """Create a Neo4j service instance."""
        from source_atlas.neo4jdb.neo4j_db import Neo4jDB
        
        # Create Neo4jDB with test credentials
        db = Neo4jDB(
            url="bolt://localhost:7687",
            user="neo4j",
            password="your_password"
        )
        service = Neo4jService(db=db)
        
        yield service
        
        # Teardown: close the driver
        db.close()
    
    def test_empty_chunks(self, neo4j_service):
        """Test that empty chunks are handled gracefully."""
        neo4j_service.import_code_chunks(chunks=[], main_branch="main")
        # Should not raise any errors
    
    def test_no_relationships_to_save(self, neo4j_service):
        """Test when there are no relationships to save."""
        chunk = CodeChunk(
            package="com.example",
            class_name="Isolated",
            full_class_name="Isolated",
            file_path="src/Isolated.java",
            content="class Isolated {}",
            ast_hash="hash_isolated",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False
        )
        
        # Import should work even with no relationships
        neo4j_service.import_code_chunks(chunks=[chunk], main_branch="main")
        
        # Cleanup
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
    
    def test_all_nodes_changed(self, neo4j_service):
        """Test when all nodes are changed (no unchanged nodes)."""
        # In this case, there should be no relationships to preserve
        # because there are no unchanged nodes
        
        chunks = [
            CodeChunk(
                package="com.example",
                class_name=f"Class{i}",
                full_class_name=f"Class{i}",
                file_path=f"src/Class{i}.java",
                content=f"class Class{i} {{}}",
                ast_hash=f"hash_{i}",
                project_id="1",
                branch="develop",
                type=ChunkType.REGULAR,
                methods=[],
                implements=(),
                used_types=(),
                parent_class=None,
                is_nested=False
            )
            for i in range(3)
        ]
        
        neo4j_service.import_code_chunks(chunks=chunks, main_branch="main")
        
        # Cleanup
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
