#!/bin/bash
# JARVIS Quick Start Script (Unix/macOS/Linux)
# Starts JARVIS in full voice mode

echo ""
echo "========================================"
echo "  JARVIS - Personal AI Assistant"
echo "========================================"
echo ""

# Activate virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Start JARVIS
python run.py "$@"
