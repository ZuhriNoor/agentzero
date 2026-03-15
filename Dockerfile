# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV TZ=UTC
ENV NO_COLOR=1
ENV TERM=dumb

# Set work directory
WORKDIR /app

# Install system dependencies required for typical Python AI/audio packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the local codebase into the container
COPY . /app/

# Ensure the data directory exists and has appropriate permissions for SQLite/JSON persistence
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Expose the API port
EXPOSE 8000

# Start the FastAPI application
CMD ["uvicorn", "agentzero_api:app", "--host", "0.0.0.0", "--port", "8000"]
