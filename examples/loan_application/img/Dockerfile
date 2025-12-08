FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install uv for faster dependency management
RUN pip install uv

# Install Python dependencies with uv
RUN uv pip install --system -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml requirements.txt ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set Python path
ENV PYTHONPATH=/app/src

# Default command
CMD ["uvicorn", "workflow_manager.main:app", "--host", "0.0.0.0", "--port", "8000"] 