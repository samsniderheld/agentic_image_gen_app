#!/bin/bash
set -e

echo "Building frontend..."
cd frontend
npm run build
cd ..

echo "Starting backend..."
cd backend
python app.py
