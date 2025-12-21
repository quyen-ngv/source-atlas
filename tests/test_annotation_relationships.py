"""
Test cases for Annotation USE relationships in Neo4j Service.

This module tests that annotation relationships are correctly created:
1. Class/Method annotations → USE relationships to annotation nodes
2. handles_annotation → reverse USE relationships (annotation USE handler)
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


class TestAnnotationRelationships:
    """Test annotation USE relationships."""
    
    def test_imports_and_setup(self):
        """Test that all imports work and basic setup is correct."""
        print("\n[TEST] Checking imports...")
        assert Neo4jService is not None
        assert CodeChunk is not None
        assert Method is not None
        print("[OK] All imports successful")
    
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
    def annotation_chunks(self) -> List[CodeChunk]:
        """
        Create annotation nodes and chunks that use them.
        
        Structure:
        - AnnotationNode: @Validation (annotation class)
        - AnnotationNode: @NotNull (annotation class)
        - HandlerClass: handles @Validation annotation
        - HandlerMethod: handles @Validation annotation (method level)
        - UserClass: uses @Validation and @NotNull annotations
        - UserMethod: uses @Validation annotation
        """
        # Annotation: @Validation
        validation_annotation = CodeChunk(
            package="com.example.annotations",
            class_name="Validation",
            full_class_name="com.example.annotations.Validation",
            file_path="src/annotations/Validation.java",
            content="@interface Validation { }",
            ast_hash="hash_validation_annotation",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        # Annotation: @NotNull
        not_null_annotation = CodeChunk(
            package="com.example.annotations",
            class_name="NotNull",
            full_class_name="com.example.annotations.NotNull",
            file_path="src/annotations/NotNull.java",
            content="@interface NotNull { }",
            ast_hash="hash_not_null_annotation",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        # Handler Class: handles @Validation annotation
        handler_method = Method(
            full_name="isValid",
            body="public boolean isValid(Object value) { return true; }",
            ast_hash="hash_handler_method",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            method_calls=(),
            used_types=(),
            inheritance_info=(),
            field_access=(),
            endpoint=(),
            handles_annotation="com.example.annotations.Validation",
            annotations=()
        )
        
        handler_class = CodeChunk(
            package="com.example.validators",
            class_name="ValidationHandler",
            full_class_name="com.example.validators.ValidationHandler",
            file_path="src/validators/ValidationHandler.java",
            content="class ValidationHandler implements ConstraintValidator<Validation, Object> { }",
            ast_hash="hash_handler_class",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[handler_method],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=False,
            annotations=(),
            handles_annotation="com.example.annotations.Validation"
        )
        
        # User Class: uses @Validation and @NotNull annotations
        user_method = Method(
            full_name="createUser",
            body="public void createUser(@Validation String name) { }",
            ast_hash="hash_user_method",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            method_calls=(),
            used_types=(),
            inheritance_info=(),
            field_access=(),
            endpoint=(),
            handles_annotation=None,
            annotations=("com.example.annotations.Validation",)
        )
        
        user_class = CodeChunk(
            package="com.example.services",
            class_name="UserService",
            full_class_name="com.example.services.UserService",
            file_path="src/services/UserService.java",
            content="@Validation class UserService { }",
            ast_hash="hash_user_class",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[user_method],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=False,
            annotations=("com.example.annotations.Validation", "com.example.annotations.NotNull"),
            handles_annotation=None
        )
        
        return [
            validation_annotation,
            not_null_annotation,
            handler_class,
            user_class
        ]
    
    def test_class_annotations_create_use_relationships(self, neo4j_service, annotation_chunks):
        """
        Test that class annotations create USE relationships.
        
        Expected:
        - UserService --USE--> Validation annotation
        - UserService --USE--> NotNull annotation
        """
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        
        # Import chunks
        neo4j_service.import_code_chunks_simple(chunks=annotation_chunks)
        
        # Verify UserService --USE--> Validation
        query = """
        MATCH (user:ClassNode {class_name: 'com.example.services.UserService', 
                               project_id: '1', branch: 'main'})
              -[:USE]->
              (validation:ClassNode {class_name: 'com.example.annotations.Validation',
                                     project_id: '1', branch: 'main'})
        WHERE user.method_name IS NULL AND validation.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "UserService should USE Validation annotation"
        
        # Verify UserService --USE--> NotNull
        query = """
        MATCH (user:ClassNode {class_name: 'com.example.services.UserService', 
                               project_id: '1', branch: 'main'})
              -[:USE]->
              (not_null:ClassNode {class_name: 'com.example.annotations.NotNull',
                                    project_id: '1', branch: 'main'})
        WHERE user.method_name IS NULL AND not_null.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "UserService should USE NotNull annotation"
    
    def test_method_annotations_create_use_relationships(self, neo4j_service, annotation_chunks):
        """
        Test that method annotations create USE relationships.
        
        Expected:
        - UserService.createUser --USE--> Validation annotation
        """
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        
        # Import chunks
        neo4j_service.import_code_chunks_simple(chunks=annotation_chunks)
        
        # Verify UserService.createUser --USE--> Validation
        query = """
        MATCH (method:MethodNode {class_name: 'com.example.services.UserService',
                                  method_name: 'createUser',
                                  project_id: '1', branch: 'main'})
              -[:USE]->
              (validation:ClassNode {class_name: 'com.example.annotations.Validation',
                                     project_id: '1', branch: 'main'})
        WHERE validation.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "UserService.createUser should USE Validation annotation"
    
    def test_handles_annotation_class_level_creates_reverse_use(self, neo4j_service, annotation_chunks):
        """
        Test that handles_annotation at class level creates reverse USE relationship.
        
        Expected:
        - Validation annotation --USE--> ValidationHandler class
        (reverse: annotation uses handler)
        """
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        
        # Import chunks
        neo4j_service.import_code_chunks_simple(chunks=annotation_chunks)
        
        # Verify Validation --USE--> ValidationHandler
        query = """
        MATCH (validation:ClassNode {class_name: 'com.example.annotations.Validation',
                                     project_id: '1', branch: 'main'})
              -[:USE]->
              (handler:ClassNode {class_name: 'com.example.validators.ValidationHandler',
                                   project_id: '1', branch: 'main'})
        WHERE validation.method_name IS NULL AND handler.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "Validation annotation should USE ValidationHandler class"
    
    def test_handles_annotation_method_level_creates_reverse_use(self, neo4j_service, annotation_chunks):
        """
        Test that handles_annotation at method level creates reverse USE relationship.
        
        Expected:
        - Validation annotation --USE--> ValidationHandler.isValid method
        (reverse: annotation uses handler method)
        """
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        
        # Import chunks
        neo4j_service.import_code_chunks_simple(chunks=annotation_chunks)
        
        # Verify Validation --USE--> ValidationHandler.isValid
        query = """
        MATCH (validation:ClassNode {class_name: 'com.example.annotations.Validation',
                                     project_id: '1', branch: 'main'})
              -[:USE]->
              (handler:MethodNode {class_name: 'com.example.validators.ValidationHandler',
                                   method_name: 'isValid',
                                   project_id: '1', branch: 'main'})
        WHERE validation.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "Validation annotation should USE ValidationHandler.isValid method"
    
    def test_multiple_annotations_on_class(self, neo4j_service):
        """
        Test that a class with multiple annotations creates multiple USE relationships.
        """
        # Create chunks with multiple annotations
        multi_annotation_class = CodeChunk(
            package="com.example",
            class_name="MultiAnnotationClass",
            full_class_name="com.example.MultiAnnotationClass",
            file_path="src/MultiAnnotationClass.java",
            content="@Validation @NotNull class MultiAnnotationClass { }",
            ast_hash="hash_multi",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=False,
            annotations=(
                "com.example.annotations.Validation",
                "com.example.annotations.NotNull",
                "com.example.annotations.Valid"
            ),
            handles_annotation=None
        )
        
        # Create annotation nodes (they need to exist for relationships to be created)
        validation = CodeChunk(
            package="com.example.annotations",
            class_name="Validation",
            full_class_name="com.example.annotations.Validation",
            file_path="src/annotations/Validation.java",
            content="@interface Validation { }",
            ast_hash="hash_val",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        not_null = CodeChunk(
            package="com.example.annotations",
            class_name="NotNull",
            full_class_name="com.example.annotations.NotNull",
            file_path="src/annotations/NotNull.java",
            content="@interface NotNull { }",
            ast_hash="hash_nn",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        valid = CodeChunk(
            package="com.example.annotations",
            class_name="Valid",
            full_class_name="com.example.annotations.Valid",
            file_path="src/annotations/Valid.java",
            content="@interface Valid { }",
            ast_hash="hash_valid",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        chunks = [validation, not_null, valid, multi_annotation_class]
        
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        
        # Import chunks
        neo4j_service.import_code_chunks_simple(chunks=chunks)
        
        # Verify all three USE relationships exist
        query = """
        MATCH (multi:ClassNode {class_name: 'com.example.MultiAnnotationClass',
                                project_id: '1', branch: 'main'})
              -[:USE]->
              (annotation:ClassNode {project_id: '1', branch: 'main'})
        WHERE multi.method_name IS NULL AND annotation.method_name IS NULL
        RETURN annotation.class_name as annotation_name
        ORDER BY annotation_name
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            annotations = [record['annotation_name'] for record in result]
            
            assert len(annotations) == 3, f"Should have 3 USE relationships, got {len(annotations)}"
            assert "com.example.annotations.NotNull" in annotations
            assert "com.example.annotations.Valid" in annotations
            assert "com.example.annotations.Validation" in annotations
    
    def test_annotation_relationships_with_branch_logic(self, neo4j_service):
        """
        Test annotation relationships work correctly with main_branch/base_branch logic.
        """
        # Create annotation in main branch
        validation_main = CodeChunk(
            package="com.example.annotations",
            class_name="Validation",
            full_class_name="com.example.annotations.Validation",
            file_path="src/annotations/Validation.java",
            content="@interface Validation { }",
            ast_hash="hash_val_main",
            project_id="1",
            branch="main",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=True,
            annotations=(),
            handles_annotation=None
        )
        
        # Create user class in develop branch that uses annotation
        user_develop = CodeChunk(
            package="com.example",
            class_name="UserClass",
            full_class_name="com.example.UserClass",
            file_path="src/UserClass.java",
            content="@Validation class UserClass { }",
            ast_hash="hash_user",
            project_id="1",
            branch="develop",
            type=ChunkType.REGULAR,
            methods=[],
            implements=(),
            used_types=(),
            parent_class=None,
            is_nested=False,
            is_annotation=False,
            annotations=("com.example.annotations.Validation",),
            handles_annotation=None
        )
        
        # Clean up
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="main")
        neo4j_service.delete_branch_nodes(project_id=1, branch_name="develop")
        
        # Import main branch first
        neo4j_service.import_code_chunks_simple(chunks=[validation_main])
        
        # Import develop branch with main_branch reference
        neo4j_service.import_code_chunks(
            chunks=[user_develop],
            main_branch="main",
            batch_size=100
        )
        
        # Verify relationship: UserClass (develop) --USE--> Validation (main)
        query = """
        MATCH (user:ClassNode {class_name: 'com.example.UserClass',
                               project_id: '1', branch: 'develop'})
              -[:USE]->
              (validation:ClassNode {class_name: 'com.example.annotations.Validation',
                                     project_id: '1', branch: 'main'})
        WHERE user.method_name IS NULL AND validation.method_name IS NULL
        RETURN count(*) as rel_count
        """
        
        with neo4j_service.db.driver.session() as session:
            result = session.run(query)
            record = result.single()
            assert record['rel_count'] == 1, "UserClass (develop) should USE Validation (main)"


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    print("=" * 80)
    print("Running Annotation Relationships Tests")
    print("=" * 80)
    
    try:
        exit_code = pytest.main([__file__, "-v", "-s", "--tb=short"])
        if exit_code == 0:
            print("\n" + "=" * 80)
            print("✅ All tests passed!")
            print("=" * 80)
        else:
            print("\n" + "=" * 80)
            print(f"❌ Tests failed with exit code: {exit_code}")
            print("=" * 80)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()

