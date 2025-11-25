# Hướng Dẫn Test và Publish Package

## ✅ Bước 1: Verify Package (Đã làm)

```bash
twine check dist/*
```

Kết quả mong đợi:
```
Checking dist/source-atlas-0.1.0.tar.gz: PASSED
Checking dist/source_atlas-0.1.0-py3-none-any.whl: PASSED
```

## 📦 Bước 2: Test Cài Đặt Local

### Option A: Test trong virtual environment mới

```bash
# Tạo venv mới để test
python -m venv test_install_venv
test_install_venv\Scripts\activate

# Cài package từ wheel file
pip install dist/source_atlas-0.1.0-py3-none-any.whl

# Test import
python -c "from source_atlas import AnalyzerFactory; print('✅ Import thành công!')"

# Test CLI
source-atlas --version

# Deactivate khi xong
deactivate
```

### Option B: Test trong project venv hiện tại

```bash
# Trong .venv hiện tại
pip install -e .

# Test
python -c "from source_atlas import AnalyzerFactory; print('✅ Import thành công!')"
source-atlas --version
```

## 🚀 Bước 3: Publish lên TestPyPI (Khuyến nghị)

### Tạo TestPyPI account & token

1. Đăng ký tại: https://test.pypi.org/account/register/
2. Tạo API token tại: https://test.pypi.org/manage/account/token/

### Upload lên TestPyPI

```bash
twine upload --repository testpypi dist/*

# Nhập:
# Username: __token__
# Password: <your-testpypi-api-token>
```

### Test cài từ TestPyPI

```bash
# Tạo venv mới
python -m venv test_pypi_venv
test_pypi_venv\Scripts\activate

# Cài từ TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ source-atlas

# Test
python -c "from source_atlas import AnalyzerFactory"
source-atlas --version

deactivate
```

## 🎯 Bước 4: Publish lên PyPI Chính Thức

**⚠️ CHỈ CHẠY KHI ĐÃ TEST KỸ!**

### Tạo PyPI account & token

1. Đăng ký tại: https://pypi.org/account/register/
2. Tạo API token tại: https://pypi.org/manage/account/token/

### Upload lên PyPI

```bash
twine upload dist/*

# Nhập:
# Username: __token__
# Password: <your-pypi-api-token>
```

### Verify trên PyPI

1. Truy cập: https://pypi.org/project/source-atlas/
2. Kiểm tra:
   - Package description hiển thị đúng
   - Dependencies đầy đủ
   - Classifiers chính xác

### Cài và test từ PyPI

```bash
# Trong venv mới
pip install source-atlas

# Test
from source_atlas import AnalyzerFactory
source-atlas --version
```

## 📝 Checklist Trước Khi Publish

- [x] Build package thành công
- [ ] `twine check dist/*` PASS
- [ ] Test cài local wheel thành công
- [ ] Import `from source_atlas import AnalyzerFactory` hoạt động
- [ ] CLI `source-atlas --version` hoạt động
- [ ] Upload lên TestPyPI thành công (khuyến nghị)
- [ ] Test cài từ TestPyPI thành công (khuyến nghị)
- [ ] README.md cập nhật hướng dẫn cài `pip install source-atlas`

## 🔄 Nếu Cần Update Version Mới

```bash
# 1. Cập nhật version trong pyproject.toml và __init__.py
# 2. Xóa dist cũ
rm -rf dist/ build/ *.egg-info

# 3. Build lại
python -m build

# 4. Upload version mới
twine upload dist/*
```

## 💡 Tips

- **Version naming**: Follow [Semantic Versioning](https://semver.org/)
  - `0.1.0` = Alpha/Initial release
  - `0.2.0` = Minor features
  - `1.0.0` = Stable production release
  
- **API Token**: Lưu tokens an toàn, KHÔNG commit vào git

- **TestPyPI**: Luôn test ở TestPyPI trước khi publish chính thức

- **Documentation**: Cập nhật README.md với installation instructions
