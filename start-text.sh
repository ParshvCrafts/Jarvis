#!/bin/bash
# JARVIS Quick Start Script (Unix/macOS/Linux) - Text Mode
# Starts JARVIS in text-only mode (no voice)

echo ""
echo "========================================"
echo "  JARVIS - Text Mode"
echo "========================================"
echo ""

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start JARVIS in text mode
python run.py --text "$@"
