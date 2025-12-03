#!/usr/bin/env bash
# run_agent.sh - simple launcher
set -e
echo "Activating venv (please ensure venv exists and is activated if not this will still try)."
source venv/bin/activate || true
python main.py
