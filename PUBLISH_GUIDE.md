# Package Testing and Publishing Guide

## ✅ Step 1: Verify Package (Completed)

```bash
twine check dist/*
```

Expected result:
```
Checking dist/source-atlas-0.1.0.tar.gz: PASSED
Checking dist/source_atlas-0.1.0-py3-none-any.whl: PASSED
```

## 📦 Step 2: Test Local Installation

### Option A: Test in a new virtual environment

```bash
# Create a new venv for testing
python -m venv test_install_venv
test_install_venv\Scripts\activate

# Install package from wheel file
pip install dist/source_atlas-0.1.0-py3-none-any.whl

# Test import
python -c "from source_atlas import AnalyzerFactory; print('✅ Import successful!')"

# Test CLI
source-atlas --version

# Deactivate when done
deactivate
```

### Option B: Test in current project venv

```bash
# In current .venv
pip install -e .

# Test
python -c "from source_atlas import AnalyzerFactory; print('✅ Import successful!')"
source-atlas --version
```

## 🚀 Step 3: Publish to TestPyPI (Recommended)

### Create TestPyPI account & token

1. Register at: https://test.pypi.org/account/register/
2. Create API token at: https://test.pypi.org/manage/account/token/

### Upload to TestPyPI

```bash
twine upload --repository testpypi dist/*

# Input:
# Username: __token__
# Password: <your-testpypi-api-token>
```

### Test installation from TestPyPI

```bash
# Create new venv
python -m venv test_pypi_venv
test_pypi_venv\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ source-atlas

# Test
python -c "from source_atlas import AnalyzerFactory"
source-atlas --version

deactivate
```

## 🎯 Step 4: Publish to Official PyPI

**⚠️ ONLY RUN AFTER THOROUGH TESTING!**

### Create PyPI account & token

1. Register at: https://pypi.org/account/register/
2. Create API token at: https://pypi.org/manage/account/token/

### Upload to PyPI

```bash
twine upload dist/*

# Input:
# Username: __token__
# Password: <your-pypi-api-token>
```

### Verify on PyPI

1. Visit: https://pypi.org/project/source-atlas/
2. Check:
   - Package description displays correctly
   - Dependencies are complete
   - Classifiers are accurate

### Install and test from PyPI

```bash
# In new venv
pip install source-atlas

# Test
from source_atlas import AnalyzerFactory
source-atlas --version
```

## 📝 Pre-Publish Checklist

- [x] Package build successful
- [ ] `twine check dist/*` PASS
- [ ] Local wheel installation test successful
- [ ] Import `from source_atlas import AnalyzerFactory` works
- [ ] CLI `source-atlas --version` works
- [ ] Upload to TestPyPI successful (recommended)
- [ ] Installation from TestPyPI successful (recommended)
- [ ] README.md updated with `pip install source-atlas` instructions

## 🔄 When Updating to New Version

```bash
# 1. Update version in pyproject.toml and __init__.py
# 2. Remove old dist
rm -rf dist/ build/ *.egg-info

# 3. Rebuild
python -m build

# 4. Upload new version
twine upload dist/*
```

## 💡 Tips

- **Version naming**: Follow [Semantic Versioning](https://semver.org/)
  - `0.1.0` = Alpha/Initial release
  - `0.2.0` = Minor features
  - `1.0.0` = Stable production release
  
- **API Token**: Store tokens securely, DO NOT commit to git

- **TestPyPI**: Always test on TestPyPI before official release

- **Documentation**: Update README.md with installation instructions
