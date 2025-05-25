#!/bin/bash

# PyroFork Forwarder Bot Startup Script
# This script handles the login process and then starts the forwarder bot

echo "🚀 Starting PyroFork Forwarder Bot..."
echo "====================================="

# Run the login script first
echo "📱 Running login process..."
python login.py

# Check if login was successful
if [ $? -eq 0 ]; then
    echo "✅ Login completed successfully!"
    echo "🤖 Starting forwarder bot..."
    python forwarder.py
else
    echo "❌ Login failed. Please check your credentials and try again."
    exit 1
fi
