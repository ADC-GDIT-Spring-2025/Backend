#!/bin/bash

# Exit on error
set -e

echo "=========================================="
echo "ETL Pipeline Setup Script"
echo "=========================================="

# Ensure we're in the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Create necessary directories if they don't exist
echo "Creating necessary directories..."
mkdir -p data
mkdir -p user_data

# Step 1: Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Warning: Virtual environment not found. Consider running setup_venv.sh first."
    echo "Continuing without virtual environment..."
fi

# Step 2: Download the Enron dataset using fetch_data.py
echo "=========================================="
echo "Step 1: Downloading Enron dataset..."
echo "=========================================="
python util/fetch_data.py

# Check if the download was successful
if [ ! -d "data/maildir" ]; then
    echo "Error: Failed to download or extract the Enron dataset."
    echo "Please check the logs above for errors."
    exit 1
fi

# Step 3: Parse the emails using parser.py
echo "=========================================="
echo "Step 2: Parsing emails..."
echo "=========================================="
echo "This may take a while depending on the size of the dataset..."

# Check if main.py exists and use it if available
python util/parser.py data/maildir

# Check if the parsing was successful
if [ ! -f "user_data/messages.json" ]; then
    echo "Error: Failed to parse emails or generate JSON files."
    echo "Please check the logs above for errors."
    exit 1
fi

echo "=========================================="
echo "ETL Pipeline Setup Complete!"
echo "=========================================="
echo "The following files have been generated:"
ls -la user_data/

echo "To deactivate the virtual environment, run: deactivate" 