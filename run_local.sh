#!/bin/bash
# Run the backend server using the virtual environment
if [ -d "venv" ]; then
    echo "Starting server using venv..."
    ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
else
    echo "Error: Virtual environment 'venv' not found."
    exit 1
fi
