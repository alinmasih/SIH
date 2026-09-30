#!/bin/bash
# Quick Setup Script for Forensics Platform
# Run this from the project root directory

set -e  # Exit on error

echo "=================================="
echo "Forensics Platform - Quick Setup"
echo "=================================="
echo ""

# Check we're in the right directory
if [ ! -f "setup.py" ]; then
    echo "❌ Error: Must run from project root (where setup.py is located)"
    exit 1
fi

echo "✓ Running from project root"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "✓ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✓ pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Runtime dependencies installed"
echo ""

echo "Installing development dependencies..."
pip install -r requirements-dev.txt --quiet
echo "✓ Development dependencies installed"
echo ""

# Install package in editable mode
echo "Installing package in editable mode..."
pip install -e .
echo "✓ Package installed"
echo ""

# Run verification
echo "=================================="
echo "Running Phase 8 Comprehensive QA..."
echo "=================================="
echo ""
python3 scripts/verify_phase8.py

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "How to launch:"
echo "  1. Launch GUI:      python3 scripts/launch_gui.py"
echo "  2. Run Test Suite:  pytest tests/ -v"
echo "  3. Check Coverage:  pytest --cov=src/forensics_platform tests/"
echo ""
echo "To install Desktop shortcut:"
echo "  cp forensics-platform.desktop ~/.local/share/applications/"
echo ""
echo "To deactivate virtualenv:"
echo "  deactivate"
echo ""
