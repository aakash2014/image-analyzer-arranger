import numpy as np
from backend.config import FACE_CONFIDENCE_THRESHOLD, MAX_FACES_PER_IMAGE
from backend.config import FACE_AUTO_MATCH_THRESHOLD, FACE_POSSIBLE_MATCH_THRESHOLD
from backend.config import FACE_PRIORITY_UNKNOWN


_model = None


def _get_model():
    global _model
    if _model is None:
        import insightface
        from insightface.app import FaceAnalysis
        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=0, det_size=(640, 640))
        _model = app
    return _model


def detect_faces(image_tensor: np.ndarray):
    app = _get_model()
    img = np.transpose(image_tensor, (1, 2, 0))
    img = (img * 255).astype(np.uint8)

    faces = app.get(img)
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


def match_faces_to_known(embeddings: list[np.ndarray], known_faces: list[dict] | None = None):
    if known_faces is None:
        known_faces = _load_known_faces()

    matches = []
    for emb in embeddings:
        best_sim = 0.0
        best_match = None
        for known in known_faces:
            known_emb = np.frombuffer(known["embedding"], dtype=np.float32)
            sim = _cosine_similarity(emb, known_emb)
            if sim > best_sim:
                best_sim = sim
                best_match = known

        if best_match is None or best_sim < FACE_POSSIBLE_MATCH_THRESHOLD:
            matches.append({"identity": None, "confidence": best_sim, "status": "unknown"})
        elif best_sim >= FACE_AUTO_MATCH_THRESHOLD:
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
