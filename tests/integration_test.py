import sys
import os
from pathlib import Path

# Add the parent directory of source_atlas to sys.path
# Assuming this script is in f:/01_projects/source_atlas/tests/integration_test.py
# We want f:/01_projects to be in sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

try:
    from analyzers.java_analyzer import JavaCodeAnalyzer
    from extractors.java.java_extractor import JavaEndpointExtractor
    from analyzers.analyzer_factory import AnalyzerFactory
    
    print("Successfully imported modules")

    try:
        analyzer = JavaCodeAnalyzer(root_path=".")
        print("Successfully instantiated JavaCodeAnalyzer")
    except Exception as e:
        print(f"Error instantiating JavaCodeAnalyzer: {e}")
        import traceback
        traceback.print_exc()

    try:
        extractor = JavaEndpointExtractor()
        print("Successfully instantiated JavaEndpointExtractor")
    except Exception as e:
        print(f"Error instantiating JavaEndpointExtractor: {e}")
        import traceback
        traceback.print_exc()
        
    try:
        factory_analyzer = AnalyzerFactory.create_analyzer("java", ".", "test_project", "main")
        print("Successfully created analyzer via factory")
    except Exception as e:
        print(f"Error creating analyzer via factory: {e}")
        import traceback
        traceback.print_exc()

except ImportError as e:
    print(f"ImportError: {e}")
    print(f"sys.path: {sys.path}")
except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()
