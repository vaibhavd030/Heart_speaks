FROM python:3.11-slim as builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies into system environment so they are available in the final stage
# We use --system because we'll just copy the site-packages
RUN uv pip install --system -r pyproject.toml

# Copy project files
COPY src/ ./src/
COPY data/ ./data/
COPY Makefile ./

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Expose Streamlit port
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "src/heart_speaks/app.py", "--server.address=0.0.0.0"]
