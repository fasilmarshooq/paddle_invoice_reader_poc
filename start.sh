#!/bin/bash

# Paddle.AI - Quick Start Script

set -e

echo "🚀 Starting Paddle.AI..."

# Create data directories
mkdir -p data/uploads data/db

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if command -v docker-compose &> /dev/null; then
    echo "📦 Using docker-compose..."
    docker-compose up --build -d
else
    echo "📦 Using docker commands..."

    # Build the image
    echo "Building Docker image..."
    docker build -t paddle-ai .

    # Stop and remove existing container if any
    docker stop paddle-ai 2>/dev/null || true
    docker rm paddle-ai 2>/dev/null || true

    # Run the container
    echo "Starting container..."
    docker run -d \
      -p 8000:8000 \
      -v "$(pwd)/data/uploads:/app/uploads" \
      -v "$(pwd)/data/db:/app/db" \
      --name paddle-ai \
      paddle-ai
fi

echo ""
echo "✅ Paddle.AI is now running!"
echo ""
echo "📍 Access the application at: http://localhost:8000"
echo "📊 View logs: docker logs -f paddle-ai"
echo "🛑 Stop: docker stop paddle-ai"
echo ""
