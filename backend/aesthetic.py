import numpy as np


def _shannon_entropy(arr: np.ndarray) -> float:
    histogram = np.histogram(arr, bins=256, range=(0, 255))[0]
    histogram = histogram / histogram.sum()
    histogram = histogram[histogram > 0]
    return -np.sum(histogram * np.log2(histogram))


def score_aesthetic(image_tensor: np.ndarray) -> float:
    img = np.transpose(image_tensor, (1, 2, 0))
    gray = np.mean(img, axis=2)

    brightness = np.mean(gray)
    contrast = np.std(gray)
    entropy = _shannon_entropy((gray * 255).astype(np.uint8))

    brightness_score = min(brightness / 0.5, 1.0) if brightness < 0.5 else min((1.0 - brightness) / 0.5, 1.0)
    brightness_score = 1.0 - brightness_score

    contrast_score = min(contrast / 0.2, 1.0)

    entropy_max = 8.0
    entropy_score = min(entropy / entropy_max, 1.0)

    score = 0.3 * brightness_score + 0.3 * contrast_score + 0.4 * entropy_score
    return min(max(score, 0.0), 1.0)
