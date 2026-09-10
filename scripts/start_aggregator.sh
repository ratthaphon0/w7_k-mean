#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
exec "$PYTHON" -m aggregator.app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
