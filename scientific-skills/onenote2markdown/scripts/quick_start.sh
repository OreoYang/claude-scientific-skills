#!/bin/bash

# OneNote to Markdown Quick Start Script
# This script helps you set up and run the OneNote to Markdown converter

set -e  # Exit on error

echo "=== OneNote to Markdown Converter ==="
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    echo "Please install Python 3.6+ and try again"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Ask for notebook name
read -p "Enter your OneNote notebook name: " notebook_name

if [ -z "$notebook_name" ]; then
    echo "Error: Notebook name cannot be empty"
    exit 1
fi

# Ask for output directory
read -p "Enter output directory (default: ./onenote_output): " output_dir
output_dir=${output_dir:-./onenote_output}

# Check if onenote-dump exists
if [ ! -d "onenote-dump" ]; then
    echo ""
    echo "Cloning onenote-dump tool..."
    git clone https://github.com/genericmoniker/onenote-dump.git
    echo "✓ Repository cloned"
fi

cd onenote-dump

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies if needed
if [ ! -f ".dependencies_installed" ]; then
    echo ""
    echo "Installing dependencies..."
    pip install -r requirements.txt -q
    touch .dependencies_installed
    echo "✓ Dependencies installed"
fi

# Set Python path
export PYTHONPATH=$(pwd)

echo ""
echo "=== Starting Conversion ==="
echo "Notebook: $notebook_name"
echo "Output: $output_dir"
echo ""

# Create output directory
mkdir -p "$output_dir"

# Run the converter
python onenote_dump/main.py "$notebook_name" "$output_dir"

echo ""
echo "=== Conversion Complete ==="
echo "Files saved to: $output_dir"
echo ""
echo "Next steps:"
echo "1. Check the converted files: ls -la $output_dir/notes/"
echo "2. View a sample file: cat $output_dir/notes/*.md | head -20"
echo "3. Import to your favorite Markdown editor"
