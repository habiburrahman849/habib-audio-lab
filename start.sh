#!/bin/bash

# Start the Flask API server in the background
echo "Starting Flask Backend on port 5000..."
python3 backend/app.py &

# Start the Next.js production server on port 7860
echo "Starting Next.js Frontend on port 7860..."
cd frontend/habib-audio-studio
npm run start -- -p 7860
