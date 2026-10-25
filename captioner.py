"""
captioner.py -- everything that is NOT user interface and NOT metrics:
  1. loading the BLIP model on the CPU
  2. turning one image into a caption
  3. safely reading images out of a ZIP file
"""

import io
import zipfile

import torch
from PIL import Image
from transformers import BlipForConditionalGeneration, BlipProcessor

import metrics

MODEL_NAME = "Salesforce/blip-image-captioning-base"  # ~990 MB, runs fine on CPU

# Safety limits so a huge/malicious ZIP cannot crash the machine
MAX_IMAGES_PER_ZIP = 30
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB per image
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def load_model():
    """Download (first time only) and load the model + its pre-processor."""
    processor = BlipProcessor.from_pretrained(MODEL_NAME)
    model = BlipForConditionalGeneration.from_pretrained(MODEL_NAME)
    model.eval()  # inference mode: switches off training-only behaviour
    metrics.MODEL_LOADED.set(1)  # Gauge -> tell Prometheus the model is in memory
    metrics.update_memory_gauge()
    return processor, model


def generate_caption(processor, model, image):
    """Caption ONE PIL image and return the caption text."""
    image = image.convert("RGB")  # BLIP expects 3 colour channels

    inputs = processor(images=image, return_tensors="pt")  # resize + normalise
    with torch.no_grad():  # no gradients needed -> faster, less RAM
        output_ids = model.generate(**inputs, max_new_tokens=30)
    return processor.decode(output_ids[0], skip_special_tokens=True)


def read_images_from_zip(zip_bytes):
    """
    Open a ZIP held in memory and return a list of (filename, PIL image).
    Anything unsuitable is skipped and counted in the SKIPPED_FILES counter.
    """
    images = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for info in archive.infolist():
            name = info.filename

            # Folders and macOS junk are not real images
            if info.is_dir() or name.startswith("__MACOSX") or name.split("/")[-1].startswith("."):
                continue

            if not name.lower().endswith(IMAGE_EXTENSIONS):
                metrics.SKIPPED_FILES.labels(reason="not_an_image").inc()
                continue

            if info.file_size > MAX_FILE_BYTES:  # size is read from the header (zip-bomb guard)
                metrics.SKIPPED_FILES.labels(reason="too_large").inc()
                continue

            if len(images) >= MAX_IMAGES_PER_ZIP:
                metrics.SKIPPED_FILES.labels(reason="over_limit").inc()
                continue

            try:
                data = archive.read(info)
                metrics.IMAGE_SIZE_BYTES.observe(len(data))
                images.append((name, Image.open(io.BytesIO(data))))
            except Exception:
                metrics.SKIPPED_FILES.labels(reason="corrupt").inc()
    return images
