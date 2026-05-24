import os

from backend.config import LOW_RESOLUTION_THRESHOLD, WHATSAPP_PATH_PATTERNS


def classify_junk(
    file_path: str,
    width: int | None,
    height: int | None,
    face_count: int,
    aesthetic_score: float,
    blur_score: float,
) -> float:
    triggered_weights = []

    if width is not None and height is not None:
        if width < LOW_RESOLUTION_THRESHOLD or height < LOW_RESOLUTION_THRESHOLD:
            triggered_weights.append(0.6)

    path_lower = file_path.lower()
    for pattern in WHATSAPP_PATH_PATTERNS:
        if pattern in path_lower:
            triggered_weights.append(0.7)
            break

    if face_count == 0 and aesthetic_score < 0.4:
        triggered_weights.append(0.4)

    if blur_score < 0.2:
        triggered_weights.append(0.5)

    if aesthetic_score < 0.2:
        triggered_weights.append(0.3)

    if not triggered_weights:
        return 0.0

    prob = 1.0
    for w in triggered_weights:
        prob *= 1.0 - w
    return round(1.0 - prob, 4)
