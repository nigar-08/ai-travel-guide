#!/bin/bash

echo "🌴 Setting up AI Travel Planner..."
echo "=========================================="

# Check if Python 3.8+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "👉 Install Python 3.8+ from https://python.org"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

echo "✅ Python and pip found"

# Install Redis
echo "📦 Installing Redis..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y redis-server
elif command -v brew &> /dev/null; then
    # macOS
    brew install redis
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y redis
else
    echo "⚠️  Please install Redis manually: https://redis.io/docs/getting-started/"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p generated_itineraries
mkdir -p logs

# Setup environment
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys"
fi

# Test Redis
echo "🔍 Testing Redis connection..."
if redis-cli ping | grep -q "PONG"; then
    echo "✅ Redis is running"
else
    echo "🚨 Starting Redis..."
    if command -v systemctl &> /dev/null; then
        sudo systemctl start redis
    elif command -v brew &> /dev/null; then
        brew services start redis
    else
        redis-server --daemonize yes
    fi
    sleep 2
fi

echo ""
echo "🎉 Setup complete!"
echo "=========================================="
echo "Next steps:"
echo "1. Edit .env file with your API keys"
echo "2. Run: python main.py (to start system)"
echo "3. Run: streamlit run app.py (for dashboard)"
echo "4. Run: python main_test.py (for demo)"
echo "=========================================="