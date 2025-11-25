"""
Test script để index Java project vào Neo4j sử dụng source-atlas package.

Hướng dẫn:
1. Sửa NEO4J_CONFIG với thông tin Neo4j của bạn
2. Sửa PROJECT_CONFIG với đường dẫn project Java của bạn
3. Chạy: python test_indexing.py
"""
import logging
import sys
import time
from pathlib import Path

from source_atlas.analyzers.analyzer_factory import AnalyzerFactory
from source_atlas.neo4jdb.neo4j_service import Neo4jService


# ============================================================
# CONFIGURATION - THAY ĐỔI CÁC GIÁ TRỊ SAU
# ============================================================

NEO4J_CONFIG = {
    "url": "bolt://localhost:7687",
    "user": "neo4j",
    "password": "12345678",  # ← THAY ĐỔI PASSWORD CỦA BẠN
}

PROJECT_CONFIG = {
    "path": "F:/01_projects/onestudy",  # ← THAY ĐỔI ĐƯỜNG DẪN PROJECT
    "id": "onestudy",
    "branch": "main",
    "language": "java",
    "output_dir": "./output/onestudy",
}

LOGGING_CONFIG = {
    "level": logging.INFO,  # Đổi thành logging.DEBUG để xem chi tiết hơn
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
}

# ============================================================
# MAIN LOGIC
# ============================================================

def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=LOGGING_CONFIG["level"],
        format=LOGGING_CONFIG["format"],
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("indexing.log"),
        ]
    )


def validate_project_path(project_path: Path) -> bool:
    """Kiểm tra project path có tồn tại không."""
    if not project_path.exists():
        logging.error(f"❌ Project path không tồn tại: {project_path}")
        return False
    return True


def analyze_project(project_path: Path):
    """Parse và phân tích Java project."""
    logger = logging.getLogger(__name__)
    logger.info(f"🔍 Bắt đầu phân tích project: {project_path}")
    
    analyzer = AnalyzerFactory.create_analyzer(
        PROJECT_CONFIG["language"],
        str(project_path),
        PROJECT_CONFIG["id"],
        PROJECT_CONFIG["branch"]
    )
    
    with analyzer as a:
        chunks = a.parse_project(project_path)
    
    logger.info(f"✅ Tìm thấy {len(chunks)} classes/interfaces/enums")
    return chunks


def export_chunks(chunks, output_path: Path):
    """Export chunks ra JSON file."""
    logger = logging.getLogger(__name__)
    
    if not output_path:
        return
    
    # Tạo analyzer instance để dùng export method
    analyzer = AnalyzerFactory.create_analyzer(
        PROJECT_CONFIG["language"],
        PROJECT_CONFIG["path"],
        PROJECT_CONFIG["id"],
        PROJECT_CONFIG["branch"]
    )
    
    analyzer.export_chunks(chunks, output_path)
    logger.info(f"💾 Đã export chunks ra: {output_path}")


def import_to_neo4j(chunks):
    """Import chunks vào Neo4j database."""
    logger = logging.getLogger(__name__)
    logger.info(f"🔗 Đang kết nối Neo4j tại {NEO4J_CONFIG['url']}...")
    
    neo4j_service = Neo4jService(
        url=NEO4J_CONFIG["url"],
        user=NEO4J_CONFIG["user"],
        password=NEO4J_CONFIG["password"]
    )
    
    import_start = time.perf_counter()
    neo4j_service.import_code_chunks(
        chunks=chunks,
        batch_size=500,
        main_branch=PROJECT_CONFIG["branch"],
        base_branch=None,
        pull_request_id=None
    )
    import_elapsed = time.perf_counter() - import_start
    
    logger.info(f"✅ Đã import {len(chunks)} chunks vào Neo4j ({import_elapsed:.2f}s)")


def main():
    """Main execution function."""
    start_time = time.perf_counter()
    
    # Setup
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Validate
    project_path = Path(PROJECT_CONFIG["path"])
    if not validate_project_path(project_path):
        return 1
    
    try:
        # Analyze
        chunks = analyze_project(project_path)
        
        # Export (optional)
        if PROJECT_CONFIG.get("output_dir"):
            export_chunks(chunks, Path(PROJECT_CONFIG["output_dir"]))
        
        # Import to Neo4j
        import_to_neo4j(chunks)
        
        # Summary
        elapsed = time.perf_counter() - start_time
        logger.info(f"\n🎉 Hoàn thành! Tổng thời gian: {elapsed:.2f}s")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Lỗi: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
