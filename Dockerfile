FROM python:3.10-slim

# Install system dependencies (ffmpeg is required for audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Set default output directory environment variable
ENV OUTPUT_DIR=/tmp/output
ENV PORT=5000

EXPOSE 5000

# Run Gunicorn WSGI production server
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 server:app
