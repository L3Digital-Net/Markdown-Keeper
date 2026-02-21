FROM mcr.microsoft.com/devcontainers/python:3.12

COPY pyproject.toml /tmp/build/
COPY src/ /tmp/build/src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -e "/tmp/build[embeddings,faiss]" \
    && pip install --no-cache-dir mypy \
    && rm -rf /tmp/build
