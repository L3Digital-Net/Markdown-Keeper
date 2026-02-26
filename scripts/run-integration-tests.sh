#!/usr/bin/env bash
# Run the integration test suite (requires devcontainer with ML dependencies).
# Usage: bash scripts/run-integration-tests.sh [pytest args...]
set -euo pipefail

echo "Checking ML dependencies..."
python -c "import sentence_transformers" 2>/dev/null || {
    echo "ERROR: sentence-transformers not installed."
    echo "Integration tests require the devcontainer environment."
    echo "  pip install -e '.[embeddings,faiss]'"
    exit 1
}
python -c "import faiss" 2>/dev/null || {
    echo "WARNING: faiss-cpu not installed. FAISS tests will use brute-force fallback."
}

echo "Running integration tests..."
python -m pytest tests/integration/ -v --tb=short "$@"
