#!/bin/bash
cd "$(dirname "$0")/bot-api" || exit
source ../.venv/bin/activate
echo "Starting API on 0.0.0.0:8000..."
uvicorn main:app --host 0.0.0.0 --port 8000
