from backend.config import (
    MEMORY_SCORE_W1, MEMORY_SCORE_W2, MEMORY_SCORE_W3, MEMORY_SCORE_W4,
    SCENE_WEIGHTS, FACE_PRIORITY_IMMEDIATE_FAMILY,
)
from backend.database import get_connection


def compute_memory_scores():
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, max_face_priority, aesthetic_score, scene_category, junk_probability
        FROM assets WHERE status = 'analyzed'
    """).fetchall()

    for row in rows:
        face_priority = row["max_face_priority"] or 0
        face_component = min(face_priority / FACE_PRIORITY_IMMEDIATE_FAMILY, 1.0)

        quality = row["aesthetic_score"] or 0.0

        scene = row["scene_category"] or "indoor"
        scene_weight = SCENE_WEIGHTS.get(scene, 0.4)

        junk = row["junk_probability"] or 0.0

        score = (
            face_component * MEMORY_SCORE_W1
            + quality * MEMORY_SCORE_W2
            + scene_weight * MEMORY_SCORE_W3
            - junk * MEMORY_SCORE_W4
        )
        score = max(0.0, min(1.0, score))

        conn.execute("UPDATE assets SET memory_score=? WHERE id=?", (score, row["id"]))
    conn.commit()
