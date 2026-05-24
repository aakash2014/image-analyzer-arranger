import threading

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_connection, init_db
from backend.scanner import scan_folder
from backend.image_pipeline import process_image
from backend.clustering import cluster_bursts, cluster_faces
from backend.scorer import compute_memory_scores
from backend.suggestion_engine import generate_suggestions

router = APIRouter()


class ScanRequest(BaseModel):
    folder: str


class ScanResponse(BaseModel):
    scan_job_id: int
    message: str


def _run_scan(scan_job_id: int, folder: str):
    conn = get_connection()
    try:
        conn.execute("UPDATE scan_jobs SET status='scanning' WHERE id=?", (scan_job_id,))
        conn.commit()

        assets = scan_folder(folder, scan_job_id)

        asset_rows = conn.execute(
            "SELECT id, file_path, width, height FROM assets WHERE status='pending'"
        ).fetchall()

        for idx, row in enumerate(asset_rows):
            process_image(row["id"], row["file_path"], row["width"], row["height"])
            conn.execute(
                "UPDATE scan_jobs SET processed_files=? WHERE id=?",
                (idx + 1, scan_job_id),
            )
            conn.commit()

        conn.execute(
            "UPDATE scan_jobs SET current_phase='clustering' WHERE id=?",
            (scan_job_id,),
        )
        conn.commit()

        cluster_bursts()

        conn.execute(
            "UPDATE scan_jobs SET current_phase='scoring' WHERE id=?",
            (scan_job_id,),
        )
        conn.commit()

        compute_memory_scores()

        conn.execute(
            "UPDATE scan_jobs SET current_phase='suggestions' WHERE id=?",
            (scan_job_id,),
        )
        conn.commit()

        generate_suggestions()

        conn.execute(
            """UPDATE scan_jobs SET status='completed', current_phase='done',
               completed_at=datetime('now') WHERE id=?""",
            (scan_job_id,),
        )
        conn.commit()

    except Exception as e:
        conn.execute(
            "UPDATE scan_jobs SET status='failed', error_message=? WHERE id=?",
            (str(e), scan_job_id),
        )
        conn.commit()
        raise


@router.post("/scan", response_model=ScanResponse)
def start_scan(req: ScanRequest):
    init_db()
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO scan_jobs (folder, status) VALUES (?, 'queued')",
        (req.folder,),
    )
    conn.commit()
    scan_job_id = cursor.lastrowid

    thread = threading.Thread(target=_run_scan, args=(scan_job_id, req.folder), daemon=True)
    thread.start()

    return ScanResponse(
        scan_job_id=scan_job_id,
        message="Scan started",
    )


@router.get("/scan/{scan_job_id}")
def get_scan_status(scan_job_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM scan_jobs WHERE id=?", (scan_job_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Scan job not found")
    return dict(row)
