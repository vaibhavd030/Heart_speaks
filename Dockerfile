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
COPY chroma_db/ ./chroma_db/
# Copy the pre-populated repository folder (contains messages.db and PDF subdirectories)
COPY All_Whispers_message/ ./All_Whispers_message/

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose FastAPI port
EXPOSE 8080

# Command to run the application - uses $PORT env var (Cloud Run sets this to 8080)
CMD ["sh", "-c", "uvicorn heart_speaks.api:app --host 0.0.0.0 --port ${PORT:-8080}"]
