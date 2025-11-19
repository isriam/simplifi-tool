#!/bin/bash

# Quicken Simplifi Web Application Startup Script

echo "🚀 Starting Quicken Simplifi Web Application..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Run ./setup.sh first!"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Run the web application
echo ""
echo "✅ Starting web server..."
echo "📍 Open your browser to: http://localhost:8000"
echo "📚 API Documentation: http://localhost:8000/docs"
echo ""
echo "⚡ Press CTRL+C to stop the server"
echo ""

python webapp.py
