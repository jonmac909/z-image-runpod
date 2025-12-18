# Z-Image RunPod Deployment

This directory contains the RunPod serverless deployment for Z-Image-Turbo text-to-image generation, used by the HistoryGen AI project.

## About Z-Image

Z-Image-Turbo is an efficient 6-billion parameter image generation model featuring a Scalable Single-Stream DiT architecture. It ranks #1 among open-source text-to-image models on the Artificial Analysis Leaderboard.

- **Speed**: Sub-second inference (8-9 steps vs 50+ for competitors)
- **Quality**: State-of-the-art open-source image generation
- **Bilingual**: Native support for English and Chinese
- **Efficiency**: Optimized for low-latency production use

## Files

- `handler.py` - RunPod serverless handler
- `Dockerfile.runpod` - Docker build configuration
- `requirements.txt` - Python dependencies
- `README.md` - This file

## Prerequisites

- Docker installed locally (for building)
- RunPod account: https://www.runpod.io/
- Docker Hub account OR GitHub integration
- HuggingFace account for model access

## Step 1: Get HuggingFace Token

1. Go to: https://huggingface.co/settings/tokens
2. Click "Create new token"
3. Name: `runpod-zimage-read`
4. Role: **Read** (not Write)
5. Copy the token (starts with `hf_...`)

## Step 2: Build Docker Image

```bash
cd z-image-runpod

# Build the image
docker build -f Dockerfile.runpod -t your-dockerhub-username/z-image-runpod:latest .

# Login to Docker Hub
docker login

# Push the image
docker push your-dockerhub-username/z-image-runpod:latest
```

**Note:** Replace `your-dockerhub-username` with your Docker Hub username.

**Alternative:** Use GitHub integration (recommended):
- RunPod can auto-build from your GitHub repo
- Push this code to GitHub
- Connect RunPod to the repository

## Step 3: Create RunPod Serverless Endpoint

1. Go to: https://www.runpod.io/console/serverless
2. Click "Create Endpoint"
3. Fill in details:
   - **Endpoint Name**: `z-image-generation`
   - **Container Image**: `your-dockerhub-username/z-image-runpod:latest` (or GitHub repo)
   - **GPU Type**: **A6000** (48GB VRAM)
   - **Container Disk**: 20GB minimum
   - **Max Workers**: 2-3 (scale based on usage)
   - **Idle Timeout**: 60 seconds
   - **Execution Timeout**: 120 seconds (2 minutes)

4. **Environment Variables** (Build-time):
   - `HF_TOKEN`: Your HuggingFace READ token

5. Click "Deploy"

## Step 4: Get Endpoint ID

After deployment, note your endpoint ID (e.g., `abc123xyz`).

The API URL will be: `https://api.runpod.ai/v2/abc123xyz`

## Step 5: Update Supabase Edge Function

Update `supabase/functions/generate-images/index.ts`:

1. Set `RUNPOD_ENDPOINT_ID` to your endpoint ID (or use env var)
2. Deploy the updated edge function
3. Add Supabase secrets:
   - `RUNPOD_API_KEY`: Your RunPod API key
   - `RUNPOD_ZIMAGE_ENDPOINT_ID`: Your endpoint ID (optional if hardcoded)

## Step 6: Test

1. Generate images from the frontend
2. Monitor RunPod dashboard for job execution
3. Check worker logs for errors
4. Verify images are generated and uploaded to Supabase storage

## Input Format

The handler expects:

```json
{
  "input": {
    "prompt": "A beautiful landscape with mountains",
    "quality": "basic",
    "aspectRatio": "16:9"
  }
}
```

**Parameters:**
- `prompt` (required): Text description of image
- `quality` (optional): `"basic"` (9 steps, fast) or `"high"` (16 steps, slower). Default: `"basic"`
- `aspectRatio` (optional): `"16:9"` (landscape), `"1:1"` (square), or `"9:16"` (portrait). Default: `"16:9"`

## Output Format

Success response:

```json
{
  "image_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
  "width": 1024,
  "height": 576,
  "steps": 9
}
```

Error response:

```json
{
  "error": "GPU out of memory. Please retry."
}
```

## Monitoring

Monitor your endpoint at: https://www.runpod.io/console/serverless

View:
- Request logs
- Execution times
- Error rates
- GPU usage
- Worker status

## Troubleshooting

### Workers crash on startup
- Check RunPod worker logs (click on crashed worker)
- Common: Model download failed → verify HF_TOKEN is set
- Common: GPU OOM during model load → use A6000 (48GB VRAM)

### Jobs timeout
- Check execution timeout setting (should be 120s minimum)
- Monitor worker logs for errors
- Verify model loads successfully on startup

### Image generation fails
- Check prompt length (max 1000 chars)
- Try different quality settings
- Monitor GPU memory usage
- Check for error messages in worker logs

### Build fails
- Verify PyTorch version matches base image (2.4.0)
- Check HuggingFace model access (Z-Image-Turbo is public)
- Ensure git is installed in Dockerfile

## Cost Optimization

- **Idle Timeout**: 60 seconds balances cold starts vs cost
- **Max Workers**: Start with 2-3, scale based on demand
- **GPU Selection**: A6000 optimal for quality/cost balance
- **Execution Timeout**: 120 seconds sufficient for most images

**Estimated Cost** (RunPod A6000 serverless):
- ~$0.79/hr when active
- Images generate in 1-3 seconds with Z-Turbo
- 10 images = ~$0.006 ($0.0006 per image)

## Performance Tips

1. **Quality Settings**:
   - Use `"basic"` (9 steps) for faster generation
   - Use `"high"` (16 steps) for better quality
   - Z-Turbo is optimized for low step counts

2. **Aspect Ratios**:
   - 16:9 (1024x576) and 1:1 (1024x1024) are fastest
   - 9:16 (576x1024) works but is less common

3. **Batch Optimization**:
   - RunPod handles concurrent requests efficiently
   - Generating 10 images in parallel is fast

## Comparison to KIE

**Advantages over KIE API:**
- ✅ Open-source (no vendor lock-in)
- ✅ Faster inference (9 steps vs 50+)
- ✅ Higher quality (#1 open-source model)
- ✅ Bilingual support (English + Chinese)
- ✅ Predictable pricing
- ✅ Full control over infrastructure

**Trade-offs:**
- Requires managing RunPod infrastructure
- Slower cold starts (model loading)
- Need to upload images to Supabase storage
- Requires HuggingFace account

## Next Steps

1. Build and deploy Docker image
2. Create RunPod endpoint with A6000 GPU
3. Update Supabase edge function
4. Test end-to-end from frontend
5. Monitor performance and adjust workers

## Resources

- [Z-Image GitHub](https://github.com/Tongyi-MAI/Z-Image)
- [Z-Image-Turbo Model Card](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo)
- [RunPod Documentation](https://docs.runpod.io/)
- [Diffusers Documentation](https://huggingface.co/docs/diffusers/)
