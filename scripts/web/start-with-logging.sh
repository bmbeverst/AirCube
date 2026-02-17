#!/bin/bash
# Start AirCube Web Dashboard with CSV logging enabled

cd "$(dirname "$0")"

# Set log directory (change this to your preferred location)
export AIRCUBE_LOG_DIR="./data/logs"

# Create log directory if it doesn't exist
mkdir -p "$AIRCUBE_LOG_DIR"

echo "CSV logging enabled: $AIRCUBE_LOG_DIR"

# Run the start script
./start.sh
