import logging
import sys
import time
from pathlib import Path

from factory.analyzer_factory import AnalyzerFactory


def main():
    """Example usage of the multi-language code analyzer."""
    start_time = time.perf_counter()

    args = {
        # "project_path": "F:/01_projects/onestudy",
        "project_path": "F:/01_projects/spring-demo",
        "project_id": "demo",
        "output": "./output/demo",
        "language": "java",
        "remove_comments": True,
        "verbose": True
    }
    
    # Configure logging - set to DEBUG to enable debug messages
    logging.basicConfig(
        level=logging.DEBUG,  # Always set to DEBUG to see debug messages
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('source_atlas.log'),
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    project_path = Path(args["project_path"])
    if not project_path.exists():
        logger.error(f"Project path {project_path} does not exist")
        return 1
    
    try:
        analyzer = AnalyzerFactory.create_analyzer(args["language"], str(project_path))
        with analyzer as a:
            chunks = a.parse_project(project_path, args["project_id"])

        logger.info(f"Found {len(chunks)} classes/interfaces/enums")

        if args["output"]:
            output_path = Path(args["output"])
            analyzer.export_chunks(chunks, output_path)
        
        logger.info(f"\nAnalysis completed successfully!")

        elapsed = time.perf_counter() - start_time
        logger.info(f"Analysis completed successfully in {elapsed:.2f} seconds!")
        return 0

    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        import traceback
        traceback.print_exc()
        print('err')
        return 1

if __name__ == "__main__":
    exit(main())