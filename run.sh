#!/bin/bash
# Start the FastAPI server
cd ~/Documents/Healthcare-Trial-Matcher
source venv/Scripts/activate
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
