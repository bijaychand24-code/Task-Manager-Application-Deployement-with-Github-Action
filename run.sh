#!/bin/bash

set -e

echo "🚀 Starting Task Manager..."

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
python -m pip install -r requirements.txt

# Start application
echo "🌐 Starting FastAPI..."
python -m uvicorn app.main:app --reload
