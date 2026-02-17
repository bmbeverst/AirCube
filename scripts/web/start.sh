#!/bin/bash
# Quick start script for AirCube Web Dashboard

cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip setuptools wheel
    ./venv/bin/pip install -r requirements.txt
fi

echo "Starting AirCube Web Dashboard..."
echo "Access at: http://localhost:5000"

# Check if log directory is configured
if [ -n "$AIRCUBE_LOG_DIR" ]; then
    echo "CSV logging: $AIRCUBE_LOG_DIR"
else
    echo "CSV logging: disabled (set AIRCUBE_LOG_DIR to enable)"
fi

echo "Press Ctrl+C to stop"
echo ""

./venv/bin/python app.py
