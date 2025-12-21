import logging
import sys
import time
from pathlib import Path

from source_atlas.analyzers.analyzer_factory import AnalyzerFactory
from source_atlas.neo4jdb.neo4j_service import Neo4jService


def main():
    """Example usage of the multi-language code analyzer."""
    start_time = time.perf_counter()

    args = {
        "project_path": "F:\\01_projects\\spring-demo",
        # "project_path": "F:\\01_projects\\spring-demo",
        "project_id": "spring-demo",
        "output": "./output/spring-demo",
        "language": "java",
        "remove_comments": True,
        "verbose": True
    }
    
    # Configure logging - set to DEBUG to enable debug messages
    logging.basicConfig(
        level=logging.INFO,  # Always set to DEBUG to see debug messages
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
        analyzer = AnalyzerFactory.create_analyzer(args["language"], str(project_path), "project_id", "branch")
        with analyzer as a:
            chunks = a.parse_project(project_path)

        logger.info(f"Found {len(chunks)} classes/interfaces/enums")

        if args["output"]:
            output_path = Path(args["output"])
            analyzer.export_chunks(chunks, output_path)

        # Import chunks vào Neo4j
        logger.info("Importing chunks to Neo4j...")
        from source_atlas.neo4jdb.neo4j_db import Neo4jDB
        
        db = Neo4jDB(
            url="bolt://localhost:7687",
            user="neo4j",
            password="your_password"
        )
        neo4j_service = Neo4jService(db=db)
        import_start = time.perf_counter()
        # Use import_code_chunks_simple for initial import
        # This ensures all relationships (including annotations) are created properly
        neo4j_service.import_code_chunks_simple(
            chunks=chunks,
            batch_size=500
        )
        import_elapsed = time.perf_counter() - import_start
        logger.info(f"Imported {len(chunks)} chunks to Neo4j in {import_elapsed:.2f} seconds")

        
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