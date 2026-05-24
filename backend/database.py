import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "photocurator.db"

_local = threading.local()


def get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA foreign_keys=ON")
    return _local.conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path       TEXT    NOT NULL UNIQUE,
            file_name       TEXT    NOT NULL,
            file_size       INTEGER NOT NULL,
            file_type       TEXT    NOT NULL,
            width           INTEGER,
            height          INTEGER,
            sha256          TEXT,
            phash           TEXT,
            timestamp       TEXT,
            gps_lat         REAL,
            gps_lon         REAL,
            camera_model    TEXT,
            orientation     INTEGER DEFAULT 1,
            status          TEXT    DEFAULT 'pending',
            face_count      INTEGER DEFAULT 0,
            face_ids        TEXT,
            max_face_priority INTEGER DEFAULT 0,
            scene_category  TEXT,
            aesthetic_score REAL,
            blur_score      REAL,
            junk_probability REAL DEFAULT 0.0,
            memory_score    REAL,
            suggested_action TEXT,
            suggestion_reason TEXT,
            cluster_role    TEXT,
            cluster_id      TEXT,
            created_at      TEXT    DEFAULT (datetime('now')),
            updated_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
        CREATE INDEX IF NOT EXISTS idx_assets_sha256 ON assets(sha256);
        CREATE INDEX IF NOT EXISTS idx_assets_phash ON assets(phash);
        CREATE INDEX IF NOT EXISTS idx_assets_memory_score ON assets(memory_score);
        CREATE INDEX IF NOT EXISTS idx_assets_junk_prob ON assets(junk_probability);

        CREATE TABLE IF NOT EXISTS faces (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id        INTEGER NOT NULL,
            embedding        BLOB,
            identity_name   TEXT,
            identity_priority INTEGER DEFAULT 1,
            confidence      REAL,
            bbox_x1         REAL,
            bbox_y1         REAL,
            bbox_x2         REAL,
            bbox_y2         REAL,
            landmark_left_eye_x  REAL,
            landmark_left_eye_y  REAL,
            landmark_right_eye_x REAL,
            landmark_right_eye_y REAL,
            FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_faces_asset ON faces(asset_id);

        CREATE TABLE IF NOT EXISTS scan_jobs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            folder          TEXT    NOT NULL,
            status          TEXT    DEFAULT 'pending',
            total_files     INTEGER DEFAULT 0,
            processed_files  INTEGER DEFAULT 0,
            current_phase   TEXT    DEFAULT 'scanning',
            error_message   TEXT,
            started_at      TEXT    DEFAULT (datetime('now')),
            completed_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS face_clusters (
            id              TEXT    PRIMARY KEY,
            label           TEXT,
            priority        INTEGER DEFAULT 1,
            face_count      INTEGER DEFAULT 0,
            centroid_embedding BLOB,
            created_at      TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS suggestions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id        INTEGER NOT NULL,
            category        TEXT    NOT NULL,
            suggested_action TEXT   NOT NULL,
            confidence      REAL    NOT NULL,
            reason          TEXT,
            user_feedback   TEXT,
            created_at      TEXT    DEFAULT (datetime('now')),
            FOREIGN KEY (asset_id) REFERENCES assets(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_suggestions_category ON suggestions(category);
        CREATE INDEX IF NOT EXISTS idx_suggestions_asset ON suggestions(asset_id);
    """)
    conn.commit()
