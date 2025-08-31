import logging
from pathlib import Path

from factory.analyzer_factory import AnalyzerFactory
from factory.config_builder import AnalyzerConfigBuilder
from lsp.implements.java_lsp import JavaLSPService
from models.domain_models import CodeChunk, DependencyGraph

def main():
    """Example usage of the multi-language code analyzer."""
    
    print('tes')
    args = {
        "project_path": "F:/_side_projects/source_atlas/data/repo/onestudy-server",
        "project_id": "onestudy-server",
        "output": "./result",
        "language": "java",  # Can be changed to 'python' or others
        "remove_comments": True,
        "verbose": True
    }
    
    # Configure logging - set to DEBUG to enable debug messages
    logging.basicConfig(
        level=logging.DEBUG,  # Always set to DEBUG to see debug messages
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('source_atlas.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    project_path = Path(args["project_path"])
    if not project_path.exists():
        logger.error(f"Project path {project_path} does not exist")
        return 1
    
    try:
        logger.info(f"Analyzing {args['language'].capitalize()} project at: {project_path}")
        
        config = AnalyzerConfigBuilder().with_comment_removal(args["remove_comments"]).build()

        analyzer = AnalyzerFactory.create_analyzer(args["language"], config, project_path)
        with analyzer as a:
            chunks, dependency_graph = a.parse_project(project_path, args["project_id"])
    
        # Display results (same as original)
        logger.info(f"\nAnalysis Results:")
        logger.info(f"Found {len(chunks)} classes/interfaces/enums")
        logger.info(f"Dependency graph has {len(dependency_graph.nodes)} nodes and {len(dependency_graph.edges)} edges")
        
        if args["output"]:
            output_path = Path(args["output"])
            analyzer.export_results(chunks, dependency_graph, output_path)
        
        logger.info(f"\nAnalysis completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        import traceback
        traceback.print_exc()
        print('err')
        return 1

if __name__ == "__main__":
    exit(main())