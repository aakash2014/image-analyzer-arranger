from typing import Optional

from fastapi import APIRouter, Query

from backend.database import get_connection

router = APIRouter()


@router.get("/suggestions")
def get_suggestions(category: Optional[str] = Query(None)):
    conn = get_connection()
    if category:
        rows = conn.execute("""
            SELECT s.id, s.asset_id, s.category, s.suggested_action,
                   s.confidence, s.reason, a.file_path, a.file_name,
                   a.memory_score, a.face_count, a.scene_category,
                   a.aesthetic_score, a.junk_probability
            FROM suggestions s
            JOIN assets a ON s.asset_id = a.id
            WHERE s.category = ?
            ORDER BY s.confidence DESC
        """, (category,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT s.id, s.asset_id, s.category, s.suggested_action,
                   s.confidence, s.reason, a.file_path, a.file_name,
                   a.memory_score, a.face_count, a.scene_category,
                   a.aesthetic_score, a.junk_probability
            FROM suggestions s
            JOIN assets a ON s.asset_id = a.id
            ORDER BY s.category, s.confidence DESC
        """).fetchall()

    grouped = {}
    for row in rows:
        cat = row["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append({
            "suggestion_id": row["id"],
            "asset_id": row["asset_id"],
            "file_path": row["file_path"],
            "file_name": row["file_name"],
            "suggested_action": row["suggested_action"],
            "confidence": row["confidence"],
            "reason": row["reason"],
            "memory_score": row["memory_score"],
            "face_count": row["face_count"],
            "scene_category": row["scene_category"],
            "aesthetic_score": row["aesthetic_score"],
            "junk_probability": row["junk_probability"],
        })

    return grouped
