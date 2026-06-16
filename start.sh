#!/usr/bin/env bash
# Start the Northwind Expense Review backend.
# Run from the project root: ./start.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo "Warning: .env not found. Copy .env.example and add your ANTHROPIC_API_KEY."
fi

echo "Starting Northwind Expense Review on http://localhost:8000 ..."
cd "$SCRIPT_DIR/backend"
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
