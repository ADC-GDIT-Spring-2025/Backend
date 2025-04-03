#!/bin/bash

# Exit on error
set -e

echo "Setting up Python virtual environment for ETL project..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 and try again."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Verify activation
echo "Virtual environment activated: $(which python)"
echo "Python version: $(python --version)"

# Install requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
else
    echo "No requirements.txt found. Skipping package installation."
    echo "You may want to create a requirements.txt file and run: pip install -r requirements.txt"
fi

echo "Setup complete! The virtual environment is now active."
echo "To deactivate the virtual environment, run: deactivate" 