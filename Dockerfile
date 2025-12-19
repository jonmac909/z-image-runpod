# RunPod Serverless Dockerfile for Z-Image Text-to-Image Generation
# Model downloads at runtime for faster builds
FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
# Note: torch/torchvision/torchaudio already in base image - do NOT reinstall
RUN pip install --no-cache-dir -r requirements.txt

# Verify diffusers installed correctly with ZImagePipeline
RUN python -c "from diffusers import ZImagePipeline; print('ZImagePipeline import OK')"

# Copy handler
COPY handler.py .

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Run the handler (model will download on first worker startup, takes ~30s)
CMD ["python", "-u", "handler.py"]
