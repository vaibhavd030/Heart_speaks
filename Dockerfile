FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into system environment
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY src/ ./src/
COPY data/ ./data/

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "heart_speaks.api:app", "--host", "0.0.0.0", "--port", "8000"]
