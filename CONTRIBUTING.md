# Contributing to Source Atlas

First off, thank you for considering contributing to Source Atlas! It's people like you that make Source Atlas such a great tool.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## 📜 Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

### Our Standards

- **Be Respectful**: Treat everyone with respect and kindness
- **Be Constructive**: Provide constructive feedback
- **Be Collaborative**: Work together towards common goals
- **Be Open**: Welcome newcomers and diverse perspectives

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Neo4j 5.x
- Basic understanding of code analysis and graph databases

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/source-atlas.git
   cd source-atlas
   ```

3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/quyen-ngv/source-atlas.git
   ```

## 💻 Development Setup

### 1. Create Virtual Environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

### 3. Set Up Pre-commit Hooks

```bash
pre-commit install
```

### 4. Configure Environment

Copy `.env.example` to `.env` and configure your settings:

```bash
cp .env.example .env
```

### 5. Set Up Neo4j

Use Docker for quick setup:

```bash
docker-compose up -d neo4j
```

Or install Neo4j Desktop from https://neo4j.com/download/

## 🤝 How to Contribute

### Types of Contributions

We welcome many types of contributions:

- 🐛 **Bug fixes**: Fix existing issues
- ✨ **New features**: Add new functionality
- 📝 **Documentation**: Improve or add documentation
- 🧪 **Tests**: Add or improve test coverage
- 🎨 **Code quality**: Refactoring and improvements
- 🌍 **Language support**: Add support for new programming languages

### Contribution Workflow

1. **Find or create an issue**: Check existing issues or create a new one
2. **Discuss**: Comment on the issue to discuss your approach
3. **Branch**: Create a feature branch from `main`
4. **Code**: Make your changes following our standards
5. **Test**: Ensure all tests pass and add new tests
6. **Commit**: Make atomic commits with clear messages
7. **Push**: Push your branch to your fork
8. **PR**: Open a pull request to the main repository

## 📏 Coding Standards

### Code Style

We use **Black** for code formatting and **Flake8** for linting:

```bash
# Format code
black .

# Check linting
flake8 .

# Type checking
mypy source_atlas/
```

### Code Guidelines

- **PEP 8**: Follow Python's PEP 8 style guide
- **Type Hints**: Use type hints for function signatures
- **Docstrings**: Add docstrings to all public functions and classes
- **Comments**: Write clear comments for complex logic
- **Naming**: Use descriptive variable and function names

### Example Code Style

```python
from typing import List, Optional
from pathlib import Path

def analyze_code_file(
    file_path: Path,
    language: str,
    options: Optional[dict] = None
) -> List[CodeChunk]:
    """
    Analyze a source code file and extract code chunks.
    
    Args:
        file_path: Path to the source file
        language: Programming language of the file
        options: Optional configuration options
        
    Returns:
        List of extracted code chunks
        
    Raises:
        ValueError: If language is not supported
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    
    # Implementation here
    ...
```

## 🧪 Testing Guidelines

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=source_atlas --cov-report=html

# Run specific test
pytest tests/test_analyzer.py::test_java_analyzer
```

### Writing Tests

- Write tests for all new features
- Maintain or improve code coverage
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)

### Example Test

```python
import pytest
from pathlib import Path
from analyzers.java_analyzer import JavaCodeAnalyzer

class TestJavaAnalyzer:
    def test_extract_class_name(self):
        # Arrange
        analyzer = JavaCodeAnalyzer(project_id="test", branch="main")
        code = "public class MyClass { }"
        
        # Act
        result = analyzer.extract_class_name(code)
        
        # Assert
        assert result == "MyClass"
```

## 🔄 Pull Request Process

### Before Submitting

- [ ] Code follows our style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated
- [ ] Commits are atomic and well-described
- [ ] Branch is up to date with main

### PR Checklist

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what changes and why
3. **Link Issue**: Reference related issues
4. **Screenshots**: Add if UI changes
5. **Testing**: Describe how you tested

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring

## Related Issues
Closes #123

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG updated
```

### Review Process

- At least one maintainer will review your PR
- Address feedback promptly
- Keep discussions respectful and constructive
- Be patient - reviews may take time

## 🐛 Reporting Bugs

### Before Reporting

1. Check existing issues
2. Test with the latest version
3. Verify it's reproducible

### Bug Report Template

Use our bug report template with:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Numbered steps to reproduce
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: OS, Python version, package versions
- **Logs**: Relevant error messages or logs

## 💡 Suggesting Features

We love feature suggestions! To suggest a feature:

1. Check if it already exists in issues
2. Create a new feature request issue
3. Describe the feature and use case
4. Explain why it would be useful

### Feature Request Template

```markdown
## Feature Description
Clear description of the feature

## Use Case
Why this feature is needed

## Proposed Solution
How you think it should work

## Alternatives
Other approaches you've considered
```

## 🏷️ Commit Message Guidelines

We follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build/tooling changes

### Examples

```bash
feat(analyzer): add support for TypeScript decorators

fix(lsp): handle connection timeout gracefully

docs(readme): update installation instructions

test(neo4j): add integration tests for graph queries
```

## 📞 Getting Help

If you need help:

- Check the [documentation](docs/)
- Search [existing issues](https://github.com/quyen-ngv/source-atlas/issues)
- Ask in [discussions](https://github.com/quyen-ngv/source-atlas/discussions)
- Contact maintainers: quyennv.4work@gmail.com

## 🎉 Recognition

Contributors will be recognized in:

- GitHub contributors page
- CHANGELOG.md for significant contributions
- README.md acknowledgments section

Thank you for contributing to Source Atlas! 🚀
