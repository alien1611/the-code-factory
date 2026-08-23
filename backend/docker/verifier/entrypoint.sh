#!/bin/bash
set -e

# Default action runs pytest, ruff, bandit and produces structured JSON outputs
CMD=${1:-"all"}

echo "=== Sandboxed Verification Running: $CMD ==="

case "$CMD" in
  "pytest")
    pytest -v --junitxml=/workspace/.evidence_pytest.xml || true
    ;;
  "ruff")
    ruff check . --output-format=json > /workspace/.evidence_ruff.json || true
    ;;
  "bandit")
    bandit -r . -f json -o /workspace/.evidence_bandit.json || true
    ;;
  "all")
    pytest -v --junitxml=/workspace/.evidence_pytest.xml || true
    ruff check . --output-format=json > /workspace/.evidence_ruff.json || true
    bandit -r . -f json -o /workspace/.evidence_bandit.json || true
    ;;
  *)
    exec "$@"
    ;;
esac

echo "=== Verification Finished ==="
