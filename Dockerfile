# Use python:3.12-slim as base
FROM python:3.12-slim

# Install system dependencies (espeak-ng for TTS, Node.js for frontend)
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    espeak-ng \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy python requirements and install
COPY requirements.txt ./
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy Next.js package files and install dependencies
COPY frontend/habib-audio-studio/package*.json ./frontend/habib-audio-studio/
WORKDIR /app/frontend/habib-audio-studio
RUN npm install

# Copy the rest of the application files
WORKDIR /app
COPY . .

# Run model downloader during build so models are baked into the container
RUN python3 download_models.py

# Build Next.js application
WORKDIR /app/frontend/habib-audio-studio
RUN npm run build

# Expose Hugging Face Space port
EXPOSE 7860

# Set start script permissions
WORKDIR /app
RUN chmod +x start.sh

# Start backend & frontend via start.sh
CMD ["./start.sh"]
