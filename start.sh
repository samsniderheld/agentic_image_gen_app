#!/bin/bash

# Single-server startup script for Agentic Image Generator

set -e

echo "==================================="
echo "Agentic Image Generator - Startup"
echo "==================================="
echo ""

# # Check if frontend is built
# if [ ! -d "frontend/dist" ]; then
#     echo "Frontend not built. Building now..."
#     echo ""
#     cd frontend
#     npm install
#     npm run build
#     cd ..
#     echo ""
#     echo "Frontend built successfully!"
#     echo ""
# fi

echo "Rebuilding Frontend"
echo ""
cd frontend
npm install
npm run build
cd ..
echo ""
echo "Frontend built successfully!"
echo ""


# Start Flask server (serves both API and frontend)
echo "Starting server on http://localhost:8000"
echo ""
cd backend
python app.py
