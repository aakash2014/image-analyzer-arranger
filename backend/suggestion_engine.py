from backend.config import (
    JUNK_PROBABILITY_THRESHOLD, TOP_MEMORY_SCORE_THRESHOLD,
    FAMILY_PRIORITY_THRESHOLD, TRAVEL_HIGHLIGHT_SCORE_THRESHOLD,
)
from backend.database import get_connection


def generate_suggestions():
    conn = get_connection()
    conn.execute("DELETE FROM suggestions")
    conn.commit()

    rows = conn.execute("""
        SELECT id, file_path, memory_score, junk_probability,
               max_face_priority, scene_category, cluster_role
        FROM assets WHERE status = 'analyzed'
    """).fetchall()

    for row in rows:
        asset_id = row["id"]
        suggestions = []

        memory_score = row["memory_score"] or 0
        junk_prob = row["junk_probability"] or 0
        face_priority = row["max_face_priority"] or 0
        cluster_role = row["cluster_role"]

        if memory_score > TOP_MEMORY_SCORE_THRESHOLD and face_priority > 0:
            suggestions.append({
                "category": "top_memories",
                "suggested_action": "KEEP",
                "confidence": round(memory_score, 4),
                "reason": f"Top memory: score {memory_score:.2f}, faces detected",
            })

        if face_priority >= FAMILY_PRIORITY_THRESHOLD:
            suggestions.append({
                "category": "family_priority",
                "suggested_action": "KEEP",
                "confidence": round(min(face_priority / 10, 1.0), 4),
                "reason": f"Family priority: face priority {face_priority}",
            })

        if cluster_role == "pruned":
            suggestions.append({
                "category": "burst_pruning",
                "suggested_action": "PRUNE",
                "confidence": 0.88,
                "reason": "Near-duplicate in burst sequence",
            })

        if junk_prob >= JUNK_PROBABILITY_THRESHOLD:
            suggestions.append({
                "category": "junk",
                "suggested_action": "DELETE_CANDIDATE",
                "confidence": round(junk_prob, 4),
                "reason": f"Junk probability: {junk_prob:.2%}",
            })

        if not suggestions:
            suggestions.append({
                "category": "needs_review",
                "suggested_action": "REVIEW",
                "confidence": round(1.0 - memory_score, 4),
                "reason": f"Memory score: {memory_score:.2f} — needs review",
            })

        for sug in suggestions:
            conn.execute("""
                INSERT INTO suggestions
                    (asset_id, category, suggested_action, confidence, reason)
                VALUES (?, ?, ?, ?, ?)
            """, (
                asset_id, sug["category"], sug["suggested_action"],
                sug["confidence"], sug["reason"],
            ))
    conn.commit()
