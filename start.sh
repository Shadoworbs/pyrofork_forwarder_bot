#!/bin/bash

# PyroFork Forwarder Bot Startup Script
# This script handles the login process and then starts the forwarder bot

echo "🚀 Starting PyroFork Forwarder Bot..."
echo "====================================="

# Check if session file exists
SESSION_FILE=$(ls *.session 2>/dev/null | head -n 1)

if [ -n "$SESSION_FILE" ]; then
    echo "📱 Session file found: $SESSION_FILE"
    echo "⏭️ Skipping login process..."
    echo "🤖 Starting forwarder bot directly..."
    python forwarder.py
else
    echo "📱 No session file found. Running login process..."
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
fi
