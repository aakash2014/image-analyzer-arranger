import numpy as np
from PIL import Image, ImageOps

from backend.config import MAX_IMAGE_DIMENSION


def load_and_preprocess(file_path: str) -> np.ndarray | None:
    try:
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        if max(w, h) > MAX_IMAGE_DIMENSION:
            ratio = MAX_IMAGE_DIMENSION / max(w, h)
            new_w = int(w * ratio)
            new_h = int(h * ratio)
            img = img.resize((new_w, new_h), Image.LANCZOS)

        arr = np.array(img, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        return arr

    except Exception as e:
        print(f"Preprocessing failed for {file_path}: {e}")
        return None


def load_pil_image(file_path: str) -> Image.Image | None:
    try:
        img = Image.open(file_path)
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception as e:
        print(f"Failed to load {file_path}: {e}")
        return None
