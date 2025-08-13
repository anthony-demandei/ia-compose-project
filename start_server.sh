#!/bin/bash

# IA Compose API - Server Startup Script
# Usage: ./start_server.sh [environment]

set -e

# Default configuration
ENVIRONMENT=${1:-development}
PORT=${PORT:-8001}
HOST=${HOST:-0.0.0.0}

echo "🚀 Starting IA Compose API"
echo "Environment: $ENVIRONMENT"
echo "Host: $HOST"
echo "Port: $PORT"

# Check required environment variables
if [ -z "$DEMANDEI_API_KEY" ]; then
    echo "❌ Error: DEMANDEI_API_KEY environment variable is required"
    echo "Please set it before starting the server:"
    echo "export DEMANDEI_API_KEY=your_api_key_here"
    exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  Warning: OPENAI_API_KEY not set (some features may not work)"
fi

# Create storage directories if they don't exist
mkdir -p storage/documents
mkdir -p storage/sessions
mkdir -p storage/uploads

echo "📁 Storage directories ready"

# Check if dependencies are installed
if ! python3 -c "import fastapi, uvicorn, pydantic" 2>/dev/null; then
    echo "❌ Error: Required dependencies not found"
    echo "Please install dependencies:"
    echo "pip install -r requirements.txt"
    exit 1
fi

echo "✅ Dependencies check passed"

# Start the server
echo "🌐 Starting FastAPI server..."

if [ "$ENVIRONMENT" = "development" ]; then
    # Development mode with auto-reload
    uvicorn main:app --host $HOST --port $PORT --reload --log-level info
elif [ "$ENVIRONMENT" = "production" ]; then
    # Production mode
    uvicorn main:app --host $HOST --port $PORT --workers 4 --log-level warning
else
    # Default mode
    uvicorn main:app --host $HOST --port $PORT --log-level info
fi