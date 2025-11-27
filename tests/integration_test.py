"""
Integration test for Source Atlas - Local source code parsing test.

This test parses a local Java project and displays the extracted code chunks.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from source_atlas.analyzers.analyzer_factory import AnalyzerFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_parse_local_project():
    """Test parsing a local Java project."""
    
    # Configure your local Java project path here
    # Example: "F:/01_projects/onestudy" or "./sample_java_project"
    project_path = input("Enter path to Java project (or press Enter for current directory): ").strip()
    if not project_path:
        project_path = "."
    
    project_path = Path(project_path).resolve()
    
    if not project_path.exists():
        logger.error(f"Project path does not exist: {project_path}")
        return
    
    logger.info(f"Parsing Java project at: {project_path}")
    
    try:
        # Create analyzer
        analyzer = AnalyzerFactory.create_analyzer(
            language="java",
            root_path=str(project_path),
            project_id="test_project",
            branch="main"
        )
        
        logger.info("Analyzer created successfully")
        
        # Parse project
        with analyzer:
            chunks = analyzer.parse_project(project_path)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"PARSING RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"Total chunks found: {len(chunks)}")
        
        # Display summary
        if chunks:
            logger.info(f"\nFirst 5 chunks:")
            for i, chunk in enumerate(chunks[:5], 1):
                logger.info(f"\n{i}. Class: {chunk.full_class_name}")
                logger.info(f"   File: {chunk.file_path}")
                logger.info(f"   Package: {chunk.package}")
                logger.info(f"   Methods: {len(chunk.methods)}")
                logger.info(f"   Type: {chunk.type}")
                
                # Display methods
                if chunk.methods:
                    logger.info(f"   Method names:")
                    for method in chunk.methods[:3]:  # Show first 3 methods
                        logger.info(f"     - {method.name}")
                    if len(chunk.methods) > 3:
                        logger.info(f"     ... and {len(chunk.methods) - 3} more")
        
        logger.info(f"\n{'='*80}")
        logger.info(f"✅ Test completed successfully!")
        logger.info(f"{'='*80}")
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error during parsing: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    print("Source Atlas - Local Source Code Parsing Test")
    print("=" * 80)
    test_parse_local_project()
