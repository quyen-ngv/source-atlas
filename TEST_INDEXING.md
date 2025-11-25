# Test Indexing Guide

## Cách Test Indexing Project

### Option 1: Development Mode (Khuyến nghị cho development)

```bash
# 1. Cài package ở development mode
cd f:\01_projects\source_atlas
.venv\Scripts\activate
pip install -e .

# 2. Chạy test script
python test_indexing.py

# Hoặc dùng main.py cũ
python main.py
```

**Ưu điểm:**
- Edit code và test ngay, không cần rebuild
- Giống môi trường development

### Option 2: Test với Installed Package

```bash
# 1. Cài package từ wheel đã build
pip install dist/source_atlas-0.1.0-py3-none-any.whl

# 2. Chạy test script
python test_indexing.py
```

**Ưu điểm:**
- Test chính xác như end-user sẽ sử dụng
- Phát hiện lỗi packaging

### Option 3: Sử dụng CLI (Sau khi cài package)

```bash
# Cài package
pip install -e .

# Sử dụng CLI
source-atlas analyze \
  --project-path F:/01_projects/onestudy \
  --language java \
  --project-id onestudy \
  --branch main \
  --output ./output/onestudy \
  --verbose
```

## Configuration

### Trong test_indexing.py

Thay đổi các giá trị trong `args`:

```python
args = {
    "project_path": "F:/01_projects/onestudy",  # ← Thay đổi đường dẫn project
    "project_id": "onestudy",                    # ← Thay đổi project ID
    "output": "./output/onestudy",               # ← Output directory
    "language": "java",                          # java, python, go, typescript
    "verbose": True                              # Debug logging
}
```

### Neo4j Configuration

Đảm bảo `.env` file có config đúng:

```env
APP_NEO4J_URL=bolt://localhost:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=your_password
APP_NEO4J_DATABASE=neo4j
```

## Troubleshooting

### Import Error

**Lỗi:** `ModuleNotFoundError: No module named 'source_atlas'`

**Giải pháp:**
```bash
# Cài lại package
pip install -e .
```

### Neo4j Connection Error

**Lỗi:** `Unable to connect to Neo4j`

**Giải pháp:**
1. Kiểm tra Neo4j đang chạy: `http://localhost:7474`
2. Kiểm tra credentials trong `.env`
3. Test connection:
   ```python
   from neo4j import GraphDatabase
   driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
   driver.verify_connectivity()
   ```

### Permissions Error

**Lỗi:** `PermissionError: [Errno 13] Permission denied`

**Giải pháp:**
- Đóng các file output nếu đang mở
- Chạy với quyền admin nếu cần

## Expected Output

```
2025-11-25 21:00:00 - __main__ - INFO - Starting analysis of java project: F:\01_projects\onestudy
2025-11-25 21:00:05 - __main__ - INFO - Found 150 classes/interfaces/enums
2025-11-25 21:00:05 - __main__ - INFO - Exported chunks to: .\output\onestudy
2025-11-25 21:00:05 - __main__ - INFO - Importing chunks to Neo4j...
2025-11-25 21:00:10 - __main__ - INFO - Imported 150 chunks to Neo4j in 5.23 seconds
2025-11-25 21:00:10 - __main__ - INFO - ✅ Analysis completed successfully in 10.45 seconds!
```

## Next Steps

Sau khi indexing thành công:

1. **Query Neo4j:**
   ```cypher
   // Xem tất cả classes
   MATCH (c:ClassNode) RETURN c LIMIT 10
   
   // Xem methods
   MATCH (m:MethodNode) RETURN m LIMIT 10
   
   // Xem relationships
   MATCH (m1:MethodNode)-[r:CALL]->(m2:MethodNode) 
   RETURN m1.name, r, m2.name LIMIT 10
   ```

2. **Check output JSON:**
   ```bash
   cat output/onestudy/chunks.json
   ```

3. **View logs:**
   ```bash
   cat test_indexing.log
   ```
