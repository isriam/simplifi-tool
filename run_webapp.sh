#!/bin/bash

# Quicken Simplifi Web Application Startup Script

echo "🚀 Starting Quicken Simplifi Web Application..."
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found!"
    echo ""
    echo "Please run the setup script first:"
    echo "  ./setup.sh"
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment."
    exit 1
fi

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "⚠️  Dependencies not found in virtual environment."
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to install dependencies."
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "You may need to create one with your Simplifi credentials."
    echo "Copy .env.example to .env and edit it."
    echo ""
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
