import numpy as np
import cv2

from backend.config import BLUR_LAPLACIAN_THRESHOLD, BLUR_MODERATE_THRESHOLD, BLUR_BLURRY_THRESHOLD


def detect_blur(image_tensor: np.ndarray) -> float:
    img = np.transpose(image_tensor, (1, 2, 0))
    img = (img * 255).astype(np.uint8)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    normalized = laplacian_var / BLUR_LAPLACIAN_THRESHOLD
    return min(max(normalized, 0.0), 1.0)
