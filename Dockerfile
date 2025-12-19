# RunPod Serverless Dockerfile for Z-Image Text-to-Image Generation
# Model downloads at runtime for faster builds
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

# Install Python dependencies with cleanup
RUN pip install --no-cache-dir -r requirements.txt \
    && pip cache purge \
    && rm -rf /tmp/* /var/tmp/* ~/.cache/*

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Run the handler (model will download on first worker startup, takes ~30s)
CMD ["python", "-u", "handler.py"]
