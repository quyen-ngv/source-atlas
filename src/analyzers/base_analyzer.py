import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from pathlib import Path
from typing import List

from models.analyzer_config import AnalyzerConfig
from models.domain_models import CodeChunk

logger = logging.getLogger(__name__)


class BaseCodeAnalyzer(ABC):

    def __init__(self, config: AnalyzerConfig):
        self.config = config

    def parse_project(self, root: Path, project_id: str) -> List[CodeChunk]:
        """
        Template method: orchestrates scanning and processing.
        Subclasses override `_get_code_files` and `_process_file`.
        """
        logger.info(f"Starting analysis for project '{project_id}' at {root}")

        code_files = self._get_code_files(root)
        if not code_files:
            logger.warning("No source files found")
            return []

        logger.info(f"Found {len(code_files)} source files")
        chunks: List[CodeChunk] = []

        for i, file in enumerate(code_files):
            logger.debug(f"[{i+1}/{len(code_files)}] Processing file: {file}")
            try:
                file_chunks = self._process_file(file, project_id)
                chunks.extend(file_chunks)
            except Exception as e:
                logger.error(f"Error processing {file}: {e}", exc_info=True)

        logger.info(f"Extracted {len(chunks)} code chunks total")
        return chunks

    def export_chunks(self, chunks: List[CodeChunk], output_path: Path) -> None:

        logger.info(f"Exporting {len(chunks)} chunks to {output_path}")
        output_path.mkdir(parents=True, exist_ok=True)
        chunks_data = [asdict(c) for c in chunks]

        with open(output_path / "chunks.json", "w", encoding="utf-8") as f:
            json.dump(chunks_data, f, indent=2, ensure_ascii=False)

    # ---- extension points ----
    @abstractmethod
    def _get_code_files(self, root: Path) -> List[Path]:
        """Return a list of relevant source files."""
        pass

    @abstractmethod
    def _process_file(self, file_path: Path, project_id: str) -> List[CodeChunk]:
        """Parse and extract code chunks from a single file."""
        pass
