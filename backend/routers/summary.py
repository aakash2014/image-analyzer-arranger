from fastapi import APIRouter

from backend.database import get_connection

router = APIRouter()


@router.get("/summary")
def get_summary():
    conn = get_connection()

    total = conn.execute("SELECT COUNT(*) as c FROM assets").fetchone()["c"]
    analyzed = conn.execute(
        "SELECT COUNT(*) as c FROM assets WHERE status='analyzed'"
    ).fetchone()["c"]
    total_faces = conn.execute(
        "SELECT COUNT(*) as c FROM faces"
    ).fetchone()["c"]

    category_counts = conn.execute("""
        SELECT category, COUNT(*) as c FROM suggestions GROUP BY category
    """).fetchall()

    top_memories = conn.execute("""
        SELECT COUNT(*) as c FROM suggestions WHERE category='top_memories'
    """).fetchone()["c"]

    family = conn.execute("""
        SELECT COUNT(*) as c FROM suggestions WHERE category='family_priority'
    """).fetchone()["c"]

    bursts = conn.execute("""
        SELECT COUNT(*) as c FROM suggestions WHERE category='burst_pruning'
    """).fetchone()["c"]

    junk = conn.execute("""
        SELECT COUNT(*) as c FROM suggestions WHERE category='junk'
    """).fetchone()["c"]

    needs_review = conn.execute("""
        SELECT COUNT(*) as c FROM suggestions WHERE category='needs_review'
    """).fetchone()["c"]

    face_clusters = conn.execute(
        "SELECT COUNT(*) as c FROM face_clusters"
    ).fetchone()["c"]

    return {
        "total_assets": total,
        "analyzed_assets": analyzed,
        "total_faces_detected": total_faces,
        "face_clusters": face_clusters,
        "suggestions": {
            "top_memories": top_memories,
            "family_priority": family,
            "burst_pruning": bursts,
            "junk": junk,
            "needs_review": needs_review,
        },
    }
