"""
Source Atlas CLI - Command Line Interface

This module provides the command-line interface for Source Atlas.
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from source_atlas.analyzers.analyzer_factory import AnalyzerFactory
from source_atlas.config.config import configs
from source_atlas.neo4jdb.neo4j_service import Neo4jService


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the application.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        
    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('source_atlas.log'),
        ]
    )
    
    return logging.getLogger(__name__)


def validate_environment():
    """Validate required environment configuration."""
    try:
        configs.validate_neo4j_config()
    except ValueError as e:
        print(f"Configuration Error: {e}", file=sys.stderr)
        print("\nPlease ensure you have:", file=sys.stderr)
        print("1. Created a .env file (copy from .env.example)", file=sys.stderr)
        print("2. Set APP_NEO4J_PASSWORD in your .env file", file=sys.stderr)
        sys.exit(1)


def analyze_command(args: argparse.Namespace) -> int:
    """
    Execute the analyze command.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger = setup_logging(args.verbose)
    start_time = time.perf_counter()
    
    # Validate environment
    validate_environment()
    
    # Validate project path
    project_path = Path(args.project_path)
    if not project_path.exists():
        logger.error(f"Project path does not exist: {project_path}")
        return 1
    
    if not project_path.is_dir():
        logger.error(f"Project path is not a directory: {project_path}")
        return 1
    
    try:
        # Create analyzer
        logger.info(f"Analyzing {args.language} project at: {project_path}")
        analyzer = AnalyzerFactory.create_analyzer(
            language=args.language,
            root_path=str(project_path),
            project_id=args.project_id,
            branch=args.branch
        )
        
        # Parse project
        with analyzer:
            chunks = analyzer.parse_project(project_path)
        
        logger.info(f"Found {len(chunks)} code chunks")
        
        # Export chunks if output path specified
        if args.output:
            output_path = Path(args.output)
            logger.info(f"Exporting chunks to: {output_path}")
            analyzer.export_chunks(chunks, output_path)
        
        # Import to Neo4j if requested
        if not args.skip_neo4j:
            logger.info("Importing chunks to Neo4j...")
            neo4j_service = Neo4jService()
            import_start = time.perf_counter()
            
            neo4j_service.import_code_chunks(
                chunks=chunks,
                batch_size=args.batch_size,
                main_branch=args.branch,
                base_branch=args.base_branch,
                pull_request_id=args.pull_request_id
            )
            
            import_elapsed = time.perf_counter() - import_start
            logger.info(f"Imported {len(chunks)} chunks to Neo4j in {import_elapsed:.2f}s")
        
        # Summary
        elapsed = time.perf_counter() - start_time
        logger.info(f"✅ Analysis completed successfully in {elapsed:.2f}s")
        return 0
        
    except Exception as e:
        logger.error(f"Error analyzing project: {e}", exc_info=args.verbose)
        return 1


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='source-atlas',
        description='Source Atlas - Multi-language code analyzer with LSP and Neo4j integration',
        epilog='For more information, visit: https://github.com/quyen-ngv/source-atlas'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='Source Atlas 0.1.0'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze a source code project'
    )
    
    analyze_parser.add_argument(
        'project_path',
        type=str,
        help='Path to the project to analyze'
    )
    
    analyze_parser.add_argument(
        '--language', '-l',
        type=str,
        required=True,
        choices=['java', 'python', 'go', 'typescript'],
        help='Programming language of the project'
    )
    
    analyze_parser.add_argument(
        '--project-id', '-p',
        type=str,
        required=True,
        help='Project identifier (used in graph database)'
    )
    
    analyze_parser.add_argument(
        '--branch', '-b',
        type=str,
        default='main',
        help='Branch name (default: main)'
    )
    
    analyze_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output directory for JSON export (optional)'
    )
    
    analyze_parser.add_argument(
        '--skip-neo4j',
        action='store_true',
        help='Skip importing to Neo4j (only export JSON)'
    )
    
    analyze_parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Batch size for Neo4j import (default: 500)'
    )
    
    analyze_parser.add_argument(
        '--base-branch',
        type=str,
        help='Base branch for comparison (optional)'
    )
    
    analyze_parser.add_argument(
        '--pull-request-id',
        type=str,
        help='Pull request ID for tracking (optional)'
    )
    
    analyze_parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose (DEBUG) logging'
    )
    
    analyze_parser.set_defaults(func=analyze_command)
    
    return parser


def main(argv: Optional[list] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv)
        
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    if not hasattr(args, 'func'):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
