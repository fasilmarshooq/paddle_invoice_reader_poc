#!/bin/bash

# Invoice Reader POC - Stop Script

set -e

echo "🛑 Stopping Invoice Reader POC..."

if command -v docker-compose &> /dev/null; then
    docker-compose down
else
    docker stop invoice-reader-poc
    docker rm invoice-reader-poc
fi

echo "✅ Container stopped and removed."
