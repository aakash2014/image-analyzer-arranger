import numpy as np
from backend.config import SCENE_CATEGORIES


def analyze_scene(image_tensor: np.ndarray) -> tuple[str, dict]:
    img = np.transpose(image_tensor, (1, 2, 0))
    gray = np.mean(img, axis=2)
    h, w = img.shape[:2]

    brightness = np.mean(gray)
    contrast = np.std(gray)

    edges_h = np.mean(np.abs(np.diff(gray, axis=0)))
    edges_v = np.mean(np.abs(np.diff(gray, axis=1)))
    edge_density = float((edges_h + edges_v) / 2)

    color_std = float(np.std(img, axis=(0, 1)).mean())

    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    green_dominance = float(np.mean(g > r + 0.05) + np.mean(g > b + 0.05)) / 2
    blue_dominance = float(np.mean(b > r + 0.05) + np.mean(b > g + 0.05)) / 2
    skin_tone_ratio = float(np.mean((r > 0.4) & (r < 0.8) & (g > 0.2) & (g < 0.6) & (b > 0.1) & (b < 0.5)))

    scores = {}
    scores["landscape"] = round(blue_dominance * 0.6 + green_dominance * 0.4, 4)
    scores["portrait"] = round(skin_tone_ratio * 0.7 + (1.0 - edge_density) * 0.3, 4)
    scores["indoor"] = round((1.0 - max(green_dominance, blue_dominance)) * (1.0 - skin_tone_ratio) * 0.5, 4)
    scores["food"] = round(skin_tone_ratio * 0.3 + color_std * 0.7, 4)
    scores["city"] = round(edge_density * 0.8 + (1.0 - green_dominance) * 0.2, 4)
    scores["nature"] = round(green_dominance * 0.8 + (1.0 - edge_density) * 0.2, 4)
    scores["event"] = round(color_std * 0.5 + skin_tone_ratio * 0.3 + (1.0 - green_dominance) * 0.2, 4)
    scores["travel"] = round(blue_dominance * 0.3 + edge_density * 0.4 + color_std * 0.3, 4)
    scores["document"] = round((1.0 - color_std) * 0.7 + edge_density * 0.3, 4)
    scores["art_meme"] = round(color_std * 0.5 + (1.0 - skin_tone_ratio) * 0.5, 4)

    total = sum(scores.values()) or 1.0
    scores = {k: round(v / total, 4) for k, v in scores.items()}

    top_category = max(scores, key=scores.get)
    return top_category, scores
