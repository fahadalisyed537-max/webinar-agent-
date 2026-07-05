#!/bin/bash

# Lead Generation AI Agent Deployment Script
# This script sets up and deploys the Lead Generation AI Agent system

set -e

echo "Deploying Lead Generation AI Agent..."

echo "1. Checking Python version..."
python3 --version

if [[ $(python3 --version | cut -d' ' -f2 | cut -d'.' -f1) -lt 3 ]]; then
    echo "ERROR: Python 3.7+ is required"
    exit 1
fi

echo "2. Installing dependencies..."
pip3 install -r requirements.txt

echo "3. Creating necessary directories..."
mkdir -p exports reports

echo "4. Setting up environment..."
if [ ! -f "config/system.json" ]; then
    echo "ERROR: config/system.json not found"
    exit 1
fi

echo "5. Running initial test..."
python3 test_leadgen.py

echo "6. Running production system..."
python3 run_leadgen.py

echo "7. Deployment complete!"
echo ""
echo "The Lead Generation AI Agent has been successfully deployed and tested."
echo ""
echo "Generated files will be available in:"
echo "- exports/: Lead data in multiple formats"
echo "- reports/: Daily/weekly/monthly reports"
echo ""
echo "To run the system automatically, add to crontab:"
echo "0 9 * * * cd $(pwd) && python3 run_leadgen.py"