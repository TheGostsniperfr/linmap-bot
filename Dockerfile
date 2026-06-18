# Build stage
FROM python:3.14-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
ENV POETRY_VERSION=2.4.1
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Copy package configurations
COPY pyproject.toml poetry.lock ./

# Configure poetry to install system-wide in builder stage
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Runtime stage
FROM python:3.14-slim AS runner

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy source code and documentation
COPY src/ ./src/
COPY README.md ./

# Create directories for secrets mount
RUN mkdir -p /app/secrets

# Set python path
ENV PYTHONPATH=/app

# Run the entrypoint
CMD ["python", "src/main.py"]
