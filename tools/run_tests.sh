#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON:-python3}"
NODE_BIN="${NODE:-node}"

if ! "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1; then
  echo "pytest is required; install with: python -m pip install -r requirements-test.txt" >&2
  exit 2
fi

if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
  echo "Node.js is required for simulator checks." >&2
  exit 2
fi

echo "== Python unit and integration tests =="
"$PYTHON_BIN" -m pytest -q tests

echo "== Self-locator standard-library smoke =="
"$PYTHON_BIN" tests/hook/smoke_self_locator.py

echo "== Simulator JavaScript checks =="
for test_file in research/simulator/test-*.js; do
  "$NODE_BIN" "$test_file"
done
"$NODE_BIN" tests/sim/test_type111_failure_twin.js

echo "== Git whitespace validation =="
git diff --check

echo "All configured offline checks passed."
