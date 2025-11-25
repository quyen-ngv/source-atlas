# Configuration Guide

Complete reference for configuring Source Atlas.

## Table of Contents

- [Environment Variables](#environment-variables)
- [Configuration File](#configuration-file)
- [CLI Options](#cli-options)
- [Neo4j Configuration](#neo4j-configuration)
- [LSP Configuration](#lsp-configuration)
- [Advanced Settings](#advanced-settings)

## Environment Variables

Source Atlas uses environment variables for configuration. Create a `.env` file in your project root:

```bash
cp .env.example .env
```

### Required Variables

#### Neo4j Connection

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `APP_NEO4J_URL` | Neo4j connection URL | `bolt://localhost:7687` | ✅ |
| `APP_NEO4J_USER` | Neo4j username | `neo4j` | ✅ |
| `APP_NEO4J_PASSWORD` | Neo4j password | `your_password` | ✅ |
| `APP_NEO4J_DATABASE` | Database name | `neo4j` | ✅ |

### Optional Variables

#### Neo4j Connection Pool

| Variable | Description | Default | Type |
|----------|-------------|---------|------|
| `NEO4J_MAX_CONNECTION_LIFETIME` | Max connection lifetime (seconds) | `30` | int |
| `NEO4J_MAX_CONNECTION_POOL_SIZE` | Max connections in pool | `50` | int |
| `NEO4J_CONNECTION_TIMEOUT` | Connection timeout (seconds) | `30.0` | float |

#### Database (PostgreSQL - Optional)

Only needed if you're using PostgreSQL in addition to Neo4j:

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_USER` | PostgreSQL username | `postgres` |
| `DB_PASSWORD` | PostgreSQL password | _(none)_ |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_DATABASE` | Database name | `source_atlas` |

#### Application Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | `source_atlas` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Configuration File

### pyproject.toml

The `pyproject.toml` file contains package metadata and tool configurations.

#### Black Configuration

```toml
[tool.black]
line-length = 120
target-version = ["py38", "py39", "py310", "py311"]
```

#### Pytest Configuration

```toml
[tool.pytest.ini_options]
addopts = "-ra -q --cov=source_atlas --cov-report=html"
testpaths = ["tests"]
```

#### MyPy Configuration

```toml
[tool.mypy]
python_version = "3.8"
ignore_missing_imports = true
```

## CLI Options

### analyze Command

Analyze a source code project:

```bash
source-atlas analyze [OPTIONS] PROJECT_PATH
```

#### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `project_path` | Path to project | `/path/to/project` |
| `--language`, `-l` | Programming language | `java`, `python`, `go`, `typescript` |
| `--project-id`, `-p` | Project identifier | `my-project` |

#### Optional Arguments

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `--branch`, `-b` | Git branch name | `main` | `--branch develop` |
| `--output`, `-o` | Output directory | _(none)_ | `--output ./output` |
| `--skip-neo4j` | Skip Neo4j import | `False` | `--skip-neo4j` |
| `--batch-size` | Neo4j batch size | `500` | `--batch-size 1000` |
| `--base-branch` | Base branch for comparison | _(none)_ | `--base-branch main` |
| `--pull-request-id` | PR ID for tracking | _(none)_ | `--pull-request-id 123` |
| `--verbose`, `-v` | Verbose logging | `False` | `--verbose` |

#### Examples

**Basic Java analysis:**
```bash
source-atlas analyze ./my-project -l java -p my-java-app
```

**With custom output:**
```bash
source-atlas analyze ./my-project -l java -p my-app -o ./analysis-output
```

**Skip Neo4j (JSON only):**
```bash
source-atlas analyze ./my-project -l python -p my-app --skip-neo4j -o ./output
```

**Verbose logging:**
```bash
source-atlas analyze ./my-project -l java -p my-app -v
```

**Pull request analysis:**
```bash
source-atlas analyze ./my-project \
  -l java \
  -p my-app \
  --branch feature/new-feature \
  --base-branch main \
  --pull-request-id 42
```

## Neo4j Configuration

### Connection Strings

#### Local Development

```bash
APP_NEO4J_URL=bolt://localhost:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=your_password
```

#### Secure Connection (TLS)

```bash
APP_NEO4J_URL=bolt+s://your-server.com:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=your_secure_password
```

#### Neo4j Aura (Cloud)

```bash
APP_NEO4J_URL=neo4j+s://xxxxx.databases.neo4j.io:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=your_aura_password
```

### Performance Tuning

#### Connection Pool Size

For high-throughput scenarios:
```bash
NEO4J_MAX_CONNECTION_POOL_SIZE=100
NEO4J_MAX_CONNECTION_LIFETIME=60
```

For resource-constrained environments:
```bash
NEO4J_MAX_CONNECTION_POOL_SIZE=10
NEO4J_MAX_CONNECTION_LIFETIME=15
```

#### Batch Import Size

Adjust based on available memory:

```bash
# Small batches (low memory)
source-atlas analyze ./project -l java -p app --batch-size 100

# Large batches (high memory)
source-atlas analyze ./project -l java -p app --batch-size 2000
```

### Database Setup

#### Create Index for Performance

```cypher
// Create indexes for fast lookups
CREATE INDEX class_full_name IF NOT EXISTS 
FOR (c:Class) ON (c.fullClassName);

CREATE INDEX method_name IF NOT EXISTS 
FOR (m:Method) ON (m.name);

CREATE INDEX file_path IF NOT EXISTS 
FOR (c:Class) ON (c.filePath);
```

## LSP Configuration

### Java LSP

Source Atlas automatically manages Java LSP servers, but you can configure:

#### JDK Path

Ensure Java JDK 11+ is in your PATH:

```bash
# Linux/Mac
export JAVA_HOME=/path/to/jdk
export PATH=$JAVA_HOME/bin:$PATH

# Windows
set JAVA_HOME=C:\Program Files\Java\jdk-11
set PATH=%JAVA_HOME%\bin;%PATH%
```

### Language-Specific Settings

#### Java Projects

Ensure `pom.xml` or `build.gradle` is present for proper Java analysis.

#### Python Projects

Python LSP uses `jedi-language-server` (automatically installed).

## Advanced Settings

### Logging Configuration

#### File Logging

Logs are written to `source_atlas.log` by default.

#### Custom Log Level

```bash
# via CLI
source-atlas analyze ./project -l java -p app --verbose

# via environment
LOG_LEVEL=DEBUG source-atlas analyze ./project -l java -p app
```

### Output Formats

#### JSON Export Structure

```json
{
  "package": "com.example",
  "className": "MyClass",
  "fullClassName": "com.example.MyClass",
  "filePath": "/path/to/MyClass.java",
  "content": "...",
  "astHash": "abc123...",
  "implements": ["Interface1", "Interface2"],
  "methods": [...]
}
```

### Docker Configuration

#### Environment Variables in Docker

```yaml
# docker-compose.yml
services:
  source-atlas:
    environment:
      - APP_NEO4J_URL=bolt://neo4j:7687
      - APP_NEO4J_USER=neo4j
      - APP_NEO4J_PASSWORD=${NEO4J_PASSWORD}
```

#### Volume Mounts

```yaml
volumes:
  # Mount project to analyze
  - ./my-project:/projects/my-project:ro
  
  # Mount output directory
  - ./output:/app/output
```

## Troubleshooting

### Neo4j Connection Issues

**Error**: `ValueError: APP_NEO4J_PASSWORD environment variable is required`

**Solution**: Set password in `.env` file:
```bash
APP_NEO4J_PASSWORD=your_actual_password
```

### LSP Server Issues

**Error**: LSP server fails to start

**Solutions**:
1. Verify Java is installed and in PATH
2. Check project has build configuration (`pom.xml`, `build.gradle`)
3. Run with `--verbose` for detailed logs

### Memory Issues

**Error**: Out of memory during large project analysis

**Solutions**:
1. Reduce batch size: `--batch-size 100`
2. Increase available memory for Neo4j
3. Process in smaller chunks

## Configuration Examples

### Development Environment

```bash
# .env
APP_NEO4J_URL=bolt://localhost:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=dev_password
NEO4J_MAX_CONNECTION_POOL_SIZE=10
LOG_LEVEL=DEBUG
```

### Production Environment

```bash
# .env
APP_NEO4J_URL=bolt+s://prod-server.com:7687
APP_NEO4J_USER=neo4j
APP_NEO4J_PASSWORD=${SECURE_PASSWORD_FROM_SECRETS}
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_TIMEOUT=60.0
LOG_LEVEL=INFO
```

### CI/CD Environment

```bash
# .env
APP_NEO4J_URL=${CI_NEO4J_URL}
APP_NEO4J_USER=${CI_NEO4J_USER}
APP_NEO4J_PASSWORD=${CI_NEO4J_PASSWORD}
NEO4J_MAX_CONNECTION_POOL_SIZE=20
```

## Best Practices

1. **Security**:
   - Never commit `.env` files
   - Use strong passwords
   - Use TLS in production
   - Rotate credentials regularly

2. **Performance**:
   - Adjust batch size based on available memory
   - Use connection pooling
   - Create Neo4j indexes

3. **Development**:
   - Use verbose logging during development
   - Export JSON for debugging
   - Test with small projects first

4. **Production**:
   - Use secure connections (bolt+s://)
   - Monitor resource usage
   - Set appropriate timeouts
   - Use environment-specific configs

## Further Reading

- [Neo4j Configuration Reference](https://neo4j.com/docs/operations-manual/current/configuration/)
- [LSP Specification](https://microsoft.github.io/language-server-protocol/)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
