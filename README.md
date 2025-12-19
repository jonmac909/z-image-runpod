# Z-Image RunPod Serverless Endpoint

Text-to-image generation using Z-Image-Turbo model on RunPod serverless infrastructure.

## 🚀 Quick Deploy

```bash
./deploy.sh
```

This will:
1. Build Docker image with cached model
2. Tag and push to RunPod registry
3. Show next steps to update endpoint

## 📁 Files

- **`handler.py`** - RunPod serverless handler for image generation
- **`Dockerfile.runpod`** - Docker image with pre-cached Z-Image-Turbo model
- **`requirements.txt`** - Python dependencies
- **`deploy.sh`** - Automated build and deploy script
- **`DEPLOY_FIXED_IMAGE.md`** - Detailed deployment guide

## 🔧 How It Works

### Input
```json
{
  "prompt": "A beautiful sunset over mountains",
  "quality": "basic",  // or "high"
  "aspectRatio": "16:9"  // or "1:1", "9:16"
}
```

### Output
```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "width": 1024,
  "height": 576,
  "steps": 9
}
```

### Quality Settings
- **basic**: 9 inference steps (~10-15 seconds)
- **high**: 16 inference steps (~20-30 seconds)

### Aspect Ratios
- **16:9**: 1024x576 (landscape)
- **1:1**: 1024x1024 (square)
- **9:16**: 576x1024 (portrait)

## 🎯 Key Features

### ✅ Model Pre-Caching
The Dockerfile pre-downloads the Z-Image-Turbo model during build, so:
- Workers start in **5-15 seconds** (not 2-5 minutes)
- No network dependencies at runtime
- Consistent, reliable performance
- No Hugging Face download failures

### ✅ Optimized for Speed
- Uses `torch.bfloat16` for efficient GPU usage
- Z-Turbo model optimized for fast generation
- Guidance scale set to 0.0 (no CFG overhead)

### ✅ Error Handling
- GPU out of memory detection
- Input validation
- Detailed logging
- Graceful error responses

## 📊 Performance

| Metric | Value |
|--------|-------|
| Worker startup | 5-15 seconds |
| Image generation (basic) | 10-15 seconds |
| Image generation (high) | 20-30 seconds |
| Model size | ~2-4 GB |
| GPU memory | ~6-8 GB |

## 🛠️ Development

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Run handler locally
python handler.py
```

### Build Docker Image
```bash
docker build -f Dockerfile.runpod -t z-image-runpod:latest .
```

### Test Locally
```bash
docker run --gpus all -p 8000:8000 z-image-runpod:latest
```

## 🔍 Troubleshooting

### Workers slow to start
- Verify the Docker image has the model cached
- Check RunPod console for the correct image tag
- Try "Force Rebuild" in RunPod settings

### GPU out of memory
- Reduce image dimensions
- Use "basic" quality instead of "high"
- Increase GPU tier in RunPod settings

### Generation fails
- Check worker logs: `node ../runpod-log-monitor.cjs -w <worker-id>`
- Verify prompt is valid and not too long (max 1000 chars)
- Check GPU availability

## 📚 Resources

- **RunPod Console**: https://www.runpod.io/console/serverless
- **Z-Image Model**: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
- **Diffusers Docs**: https://huggingface.co/docs/diffusers

## 🔗 Related

- **Endpoint ID**: `4n4m4q3itmsle2`
- **API Domain**: `api.runpod.ai` (not `.io`)
- **Web App**: https://historygenai.netlify.app/

---

**Last Updated**: December 18, 2025
**Model**: Z-Image-Turbo (Tongyi-MAI)
**Framework**: Diffusers + PyTorch
# Build trigger: Runtime model download - Wed Dec 18 18:33:00 PST 2025
