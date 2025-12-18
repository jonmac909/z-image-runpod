# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**z-image-runpod** is a RunPod serverless handler for Z-Image-Turbo text-to-image generation. It's integrated into the HistoryGen AI project as the image generation pipeline component, replacing commercial APIs with an open-source alternative.

**Model:** Z-Image-Turbo (6B parameters, #1 open-source text-to-image model)
**Infrastructure:** RunPod serverless with A6000 GPU (48GB VRAM)
**Integration:** Called by Supabase edge function, images uploaded to Supabase storage

## Development Commands

```bash
# Build Docker image
docker build -f Dockerfile -t username/z-image-runpod:latest .

# Push to Docker Hub
docker push username/z-image-runpod:latest

# Test endpoint manually
curl -X POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run \
  -H "Authorization: Bearer {API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "A cat", "quality": "basic", "aspectRatio": "16:9"}}'

# Check job status
curl https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{JOB_ID} \
  -H "Authorization: Bearer {API_KEY}"
```

## Architecture

### Handler Flow (`handler.py`)

1. **Container Startup (once per worker):**
   - Load Z-Image-Turbo model from HuggingFace (~30 seconds first time)
   - Model stays in memory for subsequent requests
   - Uses bfloat16 precision (memory efficient)

2. **Per Request:**
   - Validate input (prompt, quality, aspectRatio)
   - Map quality → inference steps (basic=9, high=16)
   - Parse aspectRatio → pixel dimensions
   - Generate image with ZImagePipeline
   - Encode to base64 PNG
   - Return {image_base64, width, height, steps}

3. **Error Handling:**
   - GPU OOM → clear cache, return error
   - Empty/invalid input → validation error
   - Model loading failure → fatal (crash worker)

### Input/Output Format

**Input:**
```json
{
  "input": {
    "prompt": "Text description (max 1000 chars)",
    "quality": "basic" | "high",
    "aspectRatio": "16:9" | "1:1" | "9:16"
  }
}
```

**Output (Success):**
```json
{
  "image_base64": "iVBORw0KGgo...",
  "width": 1024,
  "height": 576,
  "steps": 9
}
```

**Output (Error):**
```json
{
  "error": "GPU out of memory. Please retry."
}
```

### Critical Settings

**Quality → Inference Steps:**
- `basic`: 9 steps (1-3 seconds, optimal for Z-Turbo)
- `high`: 16 steps (3-5 seconds)

**Aspect Ratios → Dimensions:**
- `16:9`: 1024×576 (landscape)
- `1:1`: 1024×1024 (square)
- `9:16`: 576×1024 (portrait)

**Fixed Parameters:**
- `guidance_scale`: 0.0 (Z-Turbo optimal, not configurable)
- `torch_dtype`: bfloat16 (memory efficient)
- Device: CUDA if available, else CPU

## Critical Dependencies

### Version Requirements

**MUST match exactly:**
```
torch==2.4.0               # Must match base image
torchvision==0.19.0        # Mismatches cause "operator torchvision::nms does not exist"
torchaudio==2.4.0          # Consistency with torch version
```

**Latest from source:**
```
git+https://github.com/huggingface/diffusers  # ZImagePipeline not in stable releases
```

### Base Image

`runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04`

- PyTorch 2.4.0 (must match requirements.txt)
- CUDA 12.4.1 (GPU support)
- Python 3.11

**Image Size:** ~3.5GB base + 1GB dependencies + 13GB model = ~17GB total after first run

## Deployment

### Prerequisites

1. **HuggingFace Token:** Create at https://huggingface.co/settings/tokens (READ permission)
2. **RunPod Account:** https://www.runpod.io/
3. **GitHub Repository:** Code pushed to GitHub for RunPod integration

### RunPod Endpoint Configuration

**Required Settings:**
- **GPU Type:** A6000 (48GB VRAM) - CRITICAL, smaller GPUs will OOM
- **Container Disk:** 20GB minimum (for model download)
- **Max Workers:** 2-3 (scale based on demand)
- **Idle Timeout:** 60 seconds (balances cold starts vs cost)
- **Execution Timeout:** 120 seconds (2 minutes)
- **Environment Variable:** `HF_TOKEN=<your-token>` (for model download)

**Container Source:**
- Source: GitHub
- Repository: `jonmac909/z-image-runpod`
- Branch: `main`
- Dockerfile Path: `Dockerfile` (default, leave blank)

### Integration with HistoryGen AI

**Supabase Secrets Required:**
```
RUNPOD_API_KEY              # RunPod API key
RUNPOD_ZIMAGE_ENDPOINT_ID   # Your endpoint ID (e.g., "4n4m4q3itmsle2")
SUPABASE_URL                # For storage uploads
SUPABASE_SERVICE_ROLE_KEY   # For storage uploads
```

**Edge Function:** `/supabase/functions/generate-images/index.ts`
- Creates RunPod jobs in parallel
- Polls status every 3 seconds
- Downloads base64 images
- Uploads to Supabase storage: `generated-assets/generated-images/`
- Returns public URLs to frontend

## Common Issues

### Workers Crash on Startup

**Symptoms:** Worker status shows "Error" or "Initializing" forever

**Common Causes:**

| Error | Fix |
|-------|-----|
| `operator torchvision::nms does not exist` | Update torchvision to 0.19.0 in requirements.txt |
| `ModuleNotFoundError: No module named 'diffusers'` | Ensure diffusers from GitHub in requirements.txt |
| `CUDA out of memory` on model load | Use A6000 GPU (48GB VRAM) |
| `Failed to load model` | Set HF_TOKEN in RunPod build environment |

**Debug Process:**
1. RunPod dashboard → click endpoint → Workers tab
2. Click crashed worker → view logs
3. Find Python traceback at bottom
4. Fix issue in code
5. Push to GitHub → RunPod auto-rebuilds (5-10 min)
6. Verify worker shows "Running" status

### Jobs Timeout

**Symptoms:** Job created but never completes, times out after 120s

**Causes:**
- Model still loading on first request (check worker logs)
- GPU memory fragmentation
- Inference taking longer than expected

**Solutions:**
- Wait for worker logs to show "Z-Image model loaded successfully"
- Increase execution timeout to 180 seconds
- Use basic quality (9 steps) instead of high (16 steps)
- Restart workers if GPU memory fragmented

### Build Fails

**Symptoms:** Build shows "Failed" status, logs cut off early

**Cause:** Model pre-download during build times out or runs out of disk space

**Current Solution:** Dockerfile downloads model at runtime (not build time)
- Smaller image size
- Faster builds
- Trade-off: 30s cold start on first request

**If builds still fail:**
- Check Dockerfile path is set correctly (blank or `Dockerfile`)
- Verify GitHub repo is accessible
- Check RunPod build logs for actual error
- Try manual rebuild from RunPod dashboard

### Image Generation Fails

**Symptoms:** Job completes with error in output

**Common Errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| "GPU out of memory" | Prompt/aspect ratio too demanding | Use 16:9 instead of 1:1, try basic quality |
| "No module named ZImagePipeline" | Wrong diffusers version | Install from GitHub in requirements.txt |
| "Model not found" | HF_TOKEN missing/invalid | Regenerate token, set in RunPod environment |

### Storage Upload Fails

**Symptoms:** Job succeeds, but Supabase function logs show upload error

**Cause:** Supabase configuration missing or incorrect

**Solution:**
1. Verify `SUPABASE_SERVICE_ROLE_KEY` is set in Supabase secrets
2. Check `generated-assets` bucket exists
3. Verify bucket is public (for reading URLs)
4. Check Supabase storage quota not exceeded

## Performance Characteristics

### Timing Breakdown

**Basic Quality (9 steps):**
- Cold start (first request): 30s (model load) + 3s (inference) = 33s
- Warm requests: 1-3 seconds per image
- Base64 encoding: ~0.5s
- Storage upload: 1-2s
- **Total:** 3-6 seconds per image (after warm-up)

**High Quality (16 steps):**
- Cold start: 30s + 5s = 35s
- Warm requests: 3-5 seconds per image
- **Total:** 5-8 seconds per image (after warm-up)

**Parallelization:**
- Supabase function creates all jobs in parallel
- 10 images ≈ 6-9 seconds total (not 10 × 3 = 30s)
- Limited by RunPod worker capacity (max 2-3 workers)

### Cost Analysis

**RunPod A6000 Pricing:** ~$0.79/hour active

**Per Image:**
- 9 steps = 1-3 seconds = ~$0.0006
- 10 images ≈ $0.006

**Optimization Tips:**
- Set idle timeout to 60s (workers stay warm between requests)
- Use basic quality for most cases (imperceptible quality difference)
- Max workers 2-3 initially, scale up if needed

## Model Details

**Z-Image-Turbo Specifications:**
- 6 billion parameters
- Scalable Single-Stream DiT architecture
- #1 ranked open-source text-to-image model
- Native bilingual support (English + Chinese)
- Optimized for 8-9 inference steps (vs 50+ for competitors)

**Optimal Settings for Z-Turbo:**
- `guidance_scale`: 0.0 (no CFG, model trained for this)
- `num_inference_steps`: 9-16 (not 50+ like SDXL)
- `torch_dtype`: bfloat16 (memory efficient, no quality loss)

**Model Source:** https://huggingface.co/Tongyi-MAI/Z-Image-Turbo

## Integration Points

### Called By
`/supabase/functions/generate-images/index.ts` in HistoryGen AI project

**Function Flow:**
1. Receives prompts array from frontend
2. Creates RunPod jobs in parallel (Promise.all)
3. Polls status every 3s until complete
4. Downloads base64 images
5. Uploads to Supabase storage
6. Returns public URLs
7. Streams progress to frontend via SSE

### Frontend Usage
`src/lib/api.ts`: `generateImagesStreaming(prompts, quality, aspectRatio, onProgress)`

**Progress Events:**
- "Creating N image jobs..."
- "X/N images done"
- Final: {images: [urls], total, failed}

### Storage
**Bucket:** `generated-assets`
**Path:** `generated-images/{uuid}.png`
**Access:** Public URLs (signed)

## Critical Design Decisions

### Model Download at Runtime (Not Build)

**Decision:** Download Z-Image model on container startup, not bake into Docker image

**Rationale:**
- Smaller image: 1-2GB vs 15-20GB
- Faster deploys: Minutes vs hours
- Flexible: Update model without rebuilding

**Trade-off:** 30s cold start acceptable for serverless

### bfloat16 Precision

**Decision:** Use bfloat16 instead of float32

**Rationale:**
- Cuts memory usage in half
- Faster inference on modern GPUs
- Imperceptible quality loss
- All modern NVIDIA GPUs support it

### Fixed Aspect Ratios

**Decision:** Only support 16:9, 1:1, 9:16 with fixed pixel dimensions

**Rationale:**
- Consistent output dimensions
- Model trained on these ratios
- Avoids artifacts from non-native sizes
- Simpler implementation

## Monitoring

### Key Metrics to Watch

**Per Job:**
- Job creation time (should be <1s)
- Inference time (should be 1-5s)
- Total job time (should be 3-10s)

**Worker Health:**
- Worker status (should be "Running")
- GPU memory usage (spikes during inference)
- Error rate (should be <5%)

**Cost:**
- Worker-hours active
- Cost per image (should be $0.0003-0.001)
- Idle time percentage

### Where to Monitor

1. **RunPod Dashboard:** https://www.runpod.io/console/serverless
   - Worker status and logs
   - Job execution times
   - Error logs with tracebacks

2. **Supabase Dashboard:**
   - Edge function logs
   - Storage usage
   - Upload errors

3. **Browser Console:**
   - Streaming progress
   - Frontend errors

## Known Technical Debt

1. **Dockerfile Redundancy:** Both `Dockerfile` and `Dockerfile.runpod` exist (only need one)
2. **Diffusers Pinning:** Using GitHub main (could break with major changes)
3. **No Retry Logic:** Jobs don't retry on transient failures
4. **No Caching:** Same prompt regenerates image every time
5. **Fixed Polling:** 3s interval could be dynamic based on job status
6. **No Rate Limiting:** Frontend can spam requests
7. **Single Endpoint:** No redundancy if RunPod endpoint fails
