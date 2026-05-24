import numpy as np
import cv2

from backend.config import FACE_CONFIDENCE_THRESHOLD, MAX_FACES_PER_IMAGE
from backend.config import FACE_PRIORITY_UNKNOWN


_face_cascade = None
_insightface_model = None


def _get_face_cascade():
    global _face_cascade
    if _face_cascade is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(path)
    return _face_cascade


def _get_insightface():
    global _insightface_model
    if _insightface_model is None:
        try:
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
            app.prepare(ctx_id=0, det_size=(640, 640))
            _insightface_model = app
        except Exception:
            _insightface_model = False
    return _insightface_model if _insightface_model is not False else None


def detect_faces(image_tensor: np.ndarray) -> list[dict]:
    img = np.transpose(image_tensor, (1, 2, 0))
    img_bgr = (img * 255).astype(np.uint8)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_RGB2GRAY)

    insightface = _get_insightface()

    if insightface:
        try:
            faces = insightface.get(img_bgr)
            results = []
            for face in faces:
                if face.det_score < FACE_CONFIDENCE_THRESHOLD:
                    continue
                if len(results) >= MAX_FACES_PER_IMAGE:
                    break
                results.append({
                    "bbox": face.bbox.astype(float).tolist(),
                    "landmarks": face.landmarks.astype(float).tolist() if face.landmarks is not None else None,
                    "embedding": face.embedding.astype(np.float32),
                    "confidence": float(face.det_score),
                })
            return results
        except Exception:
            pass

    cascade = _get_face_cascade()
    detections = cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )

    results = []
    for i, (x, y, w, h) in enumerate(detections):
        if i >= MAX_FACES_PER_IMAGE:
            break
        results.append({
            "bbox": [float(x), float(y), float(x + w), float(y + h)],
            "landmarks": None,
            "embedding": None,
            "confidence": 1.0,
        })
    return results


def match_faces_to_known(embeddings: list, known_faces: list[dict] | None = None):
    if known_faces is None:
        known_faces = _load_known_faces()

    if not known_faces:
        return [{"identity": None, "confidence": 0.0, "status": "unknown"}
                for _ in embeddings]

    matches = []
    for emb in embeddings:
        if emb is None:
            matches.append({"identity": None, "confidence": 0.0, "status": "unknown"})
            continue
        best_sim = 0.0
        best_match = None
        for known in known_faces:
            known_emb = np.frombuffer(known["embedding"], dtype=np.float32)
            sim = _cosine_similarity(emb, known_emb)
            if sim > best_sim:
                best_sim = sim
                best_match = known

        if best_match is None or best_sim < 0.7:
            matches.append({"identity": None, "confidence": best_sim, "status": "unknown"})
        elif best_sim >= 0.85:
            matches.append({
                "identity": best_match["identity_name"],
                "priority": best_match.get("identity_priority", FACE_PRIORITY_UNKNOWN),
                "confidence": best_sim,
                "status": "auto_matched",
            })
        else:
            matches.append({
                "identity": best_match["identity_name"],
                "priority": best_match.get("identity_priority", FACE_PRIORITY_UNKNOWN),
                "confidence": best_sim,
                "status": "possible_match",
            })
    return matches


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def _load_known_faces():
    from backend.database import get_connection
    conn = get_connection()
    cursor = conn.execute(
        "SELECT DISTINCT identity_name, identity_priority, embedding FROM faces WHERE identity_name IS NOT NULL"
    )
    rows = cursor.fetchall()
    known_faces = {}
    for row in rows:
        name = row["identity_name"]
        if name not in known_faces:
            known_faces[name] = {
                "identity_name": row["identity_name"],
                "identity_priority": row["identity_priority"],
                "embedding": row["embedding"],
            }
        else:
            if row["identity_priority"] > known_faces[name]["identity_priority"]:
                known_faces[name]["identity_priority"] = row["identity_priority"]
    return list(known_faces.values())
