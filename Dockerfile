# Multi-stage Dockerfile for Source Atlas
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 atlasuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the package
RUN pip install --no-cache-dir -e .

# Change ownership
RUN chown -R atlasuser:atlasuser /app

# Switch to non-root user
USER atlasuser

# Default command
ENTRYPOINT ["source-atlas"]
CMD ["--help"]

# Development stage
FROM base as development

USER root
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt
USER atlasuser

# Production stage
FROM base as production

# Already configured in base
# Just use the base image as-is
