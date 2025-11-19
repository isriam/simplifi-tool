#!/bin/bash
# Setup script for Quicken Simplifi Transaction Downloader

echo "========================================="
echo "Quicken Simplifi Transaction Downloader"
echo "Setup Script"
echo "========================================="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Please install Python 3.7 or higher and try again."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"
echo ""

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Python dependencies."
    exit 1
fi

echo "✓ Python dependencies installed"
echo ""

# Install Playwright browsers
echo "Installing Playwright browsers (this may take a few minutes)..."
playwright install chromium

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install Playwright browsers."
    exit 1
fi

echo "✓ Playwright browsers installed"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ .env file created"
    echo ""
    echo "IMPORTANT: Please edit the .env file and add your credentials:"
    echo "  - SIMPLIFI_EMAIL=your_email@example.com"
    echo "  - SIMPLIFI_PASSWORD=your_password_here"
    echo ""
else
    echo "✓ .env file already exists"
    echo ""
fi

# Make scripts executable
chmod +x main.py example_usage.py

echo "========================================="
echo "Setup complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Edit .env file with your Simplifi credentials"
echo "  2. Run: python3 main.py --help"
echo "  3. Try: python3 main.py --show-browser --days 7"
echo ""
echo "For 2FA accounts, always use --show-browser flag"
echo ""
