"""
Validation test for refactored code.

This script tests the refactored java_analyzer and base_analyzer to ensure
all functionality is preserved and working correctly.
"""
import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("=" * 60)
    print("TEST 1: Module Imports")
    print("=" * 60)
    
    try:
        from analyzers.java_analyzer import JavaCodeAnalyzer
        print("✓ JavaCodeAnalyzer imported successfully")
    except Exception as e:
        print(f"✗ Failed to import JavaCodeAnalyzer: {e}")
        return False
    
    try:
        from analyzers.base_analyzer import BaseCodeAnalyzer
        print("✓ BaseCodeAnalyzer imported successfully")
    except Exception as e:
        print(f"✗ Failed to import BaseCodeAnalyzer: {e}")
        return False
    
    try:
        from utils.lsp_utils import normalize_lsp_results, extract_file_path_from_lsp
        print("✓ lsp_utils imported successfully")
    except Exception as e:
        print(f"✗ Failed to import lsp_utils: {e}")
        return False
    
    try:
        from utils.decorators import safe_extraction
        print("✓ decorators imported successfully")
    except Exception as e:
        print(f"✗ Failed to import decorators: {e}")
        return False
    
    print("\n")
    return True


def test_lsp_utils():
    """Test LSP utility functions."""
    print("=" * 60)
    print("TEST 2: LSP Utilities")
    print("=" * 60)
    
    from utils.lsp_utils import normalize_lsp_results, extract_file_path_from_lsp, extract_position_from_lsp
    
    # Test normalize_lsp_results
    result1 = normalize_lsp_results(None)
    assert result1 == [], f"Expected empty list, got {result1}"
    print("✓ normalize_lsp_results(None) returns []")
    
    result2 = normalize_lsp_results({'uri': 'test.java'})
    assert result2 == [{'uri': 'test.java'}], f"Expected list with dict, got {result2}"
    print("✓ normalize_lsp_results(dict) returns [dict]")
    
    result3 = normalize_lsp_results([{'uri': 'a.java'}, {'uri': 'b.java'}])
    assert len(result3) == 2, f"Expected 2 items, got {len(result3)}"
    print("✓ normalize_lsp_results(list) returns list")
    
    # Test extract_file_path_from_lsp
    lsp_result = {'absolutePath': '/path/to/file.java'}
    path = extract_file_path_from_lsp(lsp_result)
    assert path == '/path/to/file.java', f"Expected '/path/to/file.java', got {path}"
    print("✓ extract_file_path_from_lsp extracts absolutePath")
    
    lsp_result2 = {'uri': 'file:///path/to/file.java'}
    path2 = extract_file_path_from_lsp(lsp_result2)
    assert path2 == '/path/to/file.java', f"Expected '/path/to/file.java', got {path2}"
    print("✓ extract_file_path_from_lsp extracts from URI")
    
    # Test extract_position_from_lsp
    lsp_result3 = {'range': {'start': {'line': 10, 'character': 5}}}
    position = extract_position_from_lsp(lsp_result3)
    assert position == (10, 5), f"Expected (10, 5), got {position}"
    print("✓ extract_position_from_lsp extracts position")
    
    print("\n")
    return True



def test_java_analyzer_instantiation():
    """Test JavaCodeAnalyzer can be instantiated."""
    print("=" * 60)
    print("TEST 4: JavaCodeAnalyzer Instantiation")
    print("=" * 60)
    
    try:
        from analyzers.java_analyzer import JavaCodeAnalyzer
        
        # Test instantiation without LSP server start
        analyzer = JavaCodeAnalyzer(root_path=".", project_id="test_project", branch="main")
        print("✓ JavaCodeAnalyzer instantiated successfully")
        
        # Test abstract method implementations
        builtin_packages = analyzer._get_builtin_packages()
        assert isinstance(builtin_packages, list), "Expected list from _get_builtin_packages"
        assert len(builtin_packages) > 0, "Expected non-empty builtin packages list"
        print(f"✓ _get_builtin_packages() returns {len(builtin_packages)} packages")
        
        # Test _remove_source_prefix
        test_path = "src.main.java.com.example.MyClass"
        result = analyzer._remove_source_prefix(test_path)
        assert result == "com.example.MyClass", f"Expected 'com.example.MyClass', got {result}"
        print("✓ _remove_source_prefix() removes Java source prefix")
        
        # Test filter_builtin_items
        test_items = ["String", "com.example.MyClass", "java.util.List", "CustomClass"]
        filtered = analyzer.filter_builtin_items(test_items)
        assert "String" not in filtered, "String should be filtered"
        assert "java.util.List" not in filtered, "java.util.List should be filtered"
        assert "com.example.MyClass" in filtered, "Custom class should not be filtered"
        print(f"✓ filter_builtin_items() filtered {len(test_items) - len(filtered)} builtin items")
        
    except Exception as e:
        print(f"✗ JavaCodeAnalyzer test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n")
    return True


def test_base_analyzer_methods():
    """Test base analyzer methods."""
    print("=" * 60)
    print("TEST 5: BaseCodeAnalyzer Methods")
    print("=" * 60)
    
    try:
        from analyzers.java_analyzer import JavaCodeAnalyzer
        
        analyzer = JavaCodeAnalyzer(root_path=str(project_root), project_id="test", branch="main")
        
        # Test _extract_qualified_name_from_lsp_result
        lsp_result = {
            'absolutePath': str(project_root / 'src' / 'main' / 'java' / 'com' / 'example' / 'MyClass.java')
        }
        qualified_name = analyzer._extract_qualified_name_from_lsp_result(lsp_result)
        print(f"✓ _extract_qualified_name_from_lsp_result() returned: {qualified_name}")
        
        # Test _normalize_and_process_lsp_results
        def simple_processor(result):
            return result.get('name')
        
        test_results = [{'name': 'A'}, {'name': 'B'}, {'other': 'C'}]
        processed = analyzer._normalize_and_process_lsp_results(test_results, simple_processor)
        assert len(processed) == 2, f"Expected 2 results, got {len(processed)}"
        assert 'A' in processed and 'B' in processed, "Expected A and B in results"
        print("✓ _normalize_and_process_lsp_results() processes correctly")
        
    except Exception as e:
        print(f"✗ BaseCodeAnalyzer methods test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n")
    return True


def main():
    """Run all validation tests."""
    print("\n" + "=" * 60)
    print("VALIDATION TEST SUITE")
    print("=" * 60 + "\n")
    
    tests = [
        ("Module Imports", test_imports),
        ("LSP Utilities", test_lsp_utils),
        ("JavaCodeAnalyzer", test_java_analyzer_instantiation),
        ("BaseCodeAnalyzer Methods", test_base_analyzer_methods),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ {test_name} FAILED with exception: {e}\n")
            import traceback
            traceback.print_exc()
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{len(tests)} tests passed")
    if failed == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print(f"❌ {failed} test(s) FAILED")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
