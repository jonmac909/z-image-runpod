# RunPod Serverless Dockerfile for Z-Image Text-to-Image Generation
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
COPY handler.py .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Run the handler (model will download on first startup)
CMD ["python", "-u", "handler.py"]
