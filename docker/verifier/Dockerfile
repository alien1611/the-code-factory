FROM python:3.11-slim

# Install system utilities and security tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install verification and test execution tools
RUN pip install --no-cache-dir \
    pytest \
    ruff \
    bandit

# Create non-root user for safe sandbox execution
RUN useradd -m -u 1000 sandboxuser

WORKDIR /workspace
RUN chown -R sandboxuser:sandboxuser /workspace

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER sandboxuser

ENTRYPOINT ["/entrypoint.sh"]
