#!/bin/bash
# Kraken Z53 LCD Monitor Launcher
# Automatically activates venv and runs the monitor

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"

# Check if venv exists
if [ ! -d "$VENV_DIR" ]; then
    echo "ERROR: Virtual environment not found at $VENV_DIR"
    echo "Please run setup first:"
    echo "  python3 -m venv .venv"
    echo "  .venv/bin/pip install -r requirements.txt"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$SCRIPT_DIR/kraken_monitor.py" ]; then
    echo "ERROR: kraken_monitor.py not found in $SCRIPT_DIR"
    exit 1
fi

# Activate venv and run
echo "Starting Kraken Z53 LCD Monitor..."
echo "Using Python: $PYTHON"
echo ""

exec "$PYTHON" "$SCRIPT_DIR/kraken_monitor.py" "$@"
