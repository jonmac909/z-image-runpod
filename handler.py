"""
RunPod Handler for Z-Image Text-to-Image Generation

This handler accepts text prompts and generates images using the Z-Image-Turbo model.
It supports quality settings (basic/high) and aspect ratio customization.

Input: { prompt, quality, aspectRatio }
Output: { image_base64, width, height }
"""

import runpod
import torch
import base64
from io import BytesIO
import logging

from diffusers import ZImagePipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize model (load once on container start)
logger.info("Loading Z-Image model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")

try:
    pipe = ZImagePipeline.from_pretrained(
        "Tongyi-MAI/Z-Image-Turbo",
        torch_dtype=torch.bfloat16
    ).to(device)
    logger.info("Z-Image model loaded successfully")
except Exception as e:
    logger.error(f"FATAL: Failed to load Z-Image model: {e}", exc_info=True)
    raise


def parse_aspect_ratio(aspect_ratio: str) -> tuple:
    """
    Parse aspect ratio string to width/height pixels

    Args:
        aspect_ratio: Aspect ratio string (e.g., "16:9", "1:1", "9:16")

    Returns:
        Tuple of (width, height) in pixels (both divisible by 16)
    """
    ratios = {
        "16:9": (1792, 1008),  # Landscape HD (closest to 1080p with exact 16:9 ratio, divisible by 16)
        "1:1": (1024, 1024),   # Square (native training res)
        "9:16": (1008, 1792),  # Portrait HD (vertical)
    }
    return ratios.get(aspect_ratio, (1024, 1024))  # Default to square


def handler(job):
    """
    RunPod handler function for Z-Image generation

    Expected input format:
    {
        "prompt": "Text description of image to generate",
        "quality": "basic" or "high" (default: "basic"),
        "aspectRatio": "16:9", "1:1", or "9:16" (default: "16:9")
    }

    Returns:
    {
        "image_base64": "base64_encoded_png_image",
        "width": 1024,
        "height": 576
    }

    Or on error:
    {
        "error": "Error message"
    }
    """
    try:
        # Extract and validate input
        job_input = job.get("input", {})
        prompt = job_input.get("prompt", "").strip()
        quality = job_input.get("quality", "basic")
        aspect_ratio = job_input.get("aspectRatio", "16:9")
        # Allow custom width/height override for testing
        custom_width = job_input.get("width")
        custom_height = job_input.get("height")

        # Validate prompt
        if not prompt:
            logger.error("No prompt provided")
            return {"error": "No prompt provided"}

        if len(prompt) > 1000:
            logger.warning(f"Prompt too long ({len(prompt)} chars), truncating to 1000")
            prompt = prompt[:1000]

        logger.info(f"Generating image: quality={quality}, aspect={aspect_ratio}")
        logger.info(f"Prompt: {prompt[:100]}...")

        # Map quality to inference steps
        # basic: 9 steps (fast, optimized for Z-Turbo)
        # high: 16 steps (higher quality, slower)
        num_steps = 9 if quality == "basic" else 16
        logger.info(f"Using {num_steps} inference steps")

        # Parse aspect ratio to dimensions (or use custom override)
        if custom_width and custom_height:
            width, height = int(custom_width), int(custom_height)
            # Validate dimensions are divisible by 16 (required by the model)
            if width % 16 != 0:
                return {"error": f"Width must be divisible by 16 (got {width}). Please adjust the width to a multiple of 16."}
            if height % 16 != 0:
                return {"error": f"Height must be divisible by 16 (got {height}). Please adjust the height to a multiple of 16."}
            logger.info(f"Using custom dimensions: {width}x{height}")
        else:
            width, height = parse_aspect_ratio(aspect_ratio)
            logger.info(f"Image dimensions: {width}x{height}")

        # Generate image
        try:
            logger.info("Starting image generation...")
            image = pipe(
                prompt=prompt,
                height=height,
                width=width,
                num_inference_steps=num_steps,
                guidance_scale=0.0,  # Z-Turbo optimized for 0.0 (no CFG)
            ).images[0]
            logger.info("Image generation completed")

        except torch.cuda.OutOfMemoryError:
            logger.error("GPU out of memory during generation")
            # Clear GPU cache and return error
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            return {"error": "GPU out of memory. Please try with a different aspect ratio or retry."}

        except RuntimeError as e:
            logger.error(f"Runtime error during generation: {e}", exc_info=True)
            return {"error": f"Generation failed: {str(e)}"}

        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}", exc_info=True)
            return {"error": f"Image generation failed: {str(e)}"}

        # Convert PIL Image to base64 PNG
        try:
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            image_bytes = buffer.getvalue()

            if len(image_bytes) == 0:
                logger.error("Generated image is empty")
                return {"error": "Generated image is empty"}

            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            logger.info(f"Image encoded to base64: {len(image_base64)} chars ({len(image_bytes)} bytes)")

        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}", exc_info=True)
            return {"error": f"Image encoding failed: {str(e)}"}

        # Return result
        return {
            "image_base64": image_base64,
            "width": width,
            "height": height,
            "steps": num_steps
        }

    except KeyError as e:
        logger.error(f"Missing required field: {e}")
        return {"error": f"Missing required field: {str(e)}"}

    except Exception as e:
        logger.error(f"Unexpected handler error: {e}", exc_info=True)
        return {"error": f"Unexpected error: {str(e)}"}


if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler for Z-Image")
    runpod.serverless.start({"handler": handler})
