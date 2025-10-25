#!/bin/bash

echo "🚀 Setting up TACP-Core Demo..."

if ! docker ps | grep -q redis; then
    echo "🐳 Starting Redis container..."
    docker run --name redis -p 6379:6379 -d redis > /dev/null 2>&1
    sleep 2
fi

if [ ! -f "venv/bin/activate" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "🧪 Running TACP Demo..."
python main_test.py
