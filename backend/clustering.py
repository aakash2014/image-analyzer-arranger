from collections import defaultdict

import numpy as np

from backend.config import BURST_TIME_GAP_SECONDS, BURST_PHASH_DISTANCE
from backend.config import BURST_HERO_COUNT, BURST_BACKUP_COUNT
from backend.database import get_connection


def _phash_distance(hex1: str, hex2: str) -> int:
    int1 = int(hex1, 16)
    int2 = int(hex2, 16)
    return bin(int1 ^ int2).count("1")


def cluster_bursts():
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, file_path, phash, timestamp, aesthetic_score
        FROM assets
        WHERE timestamp IS NOT NULL AND phash IS NOT NULL
          AND status = 'analyzed'
        ORDER BY timestamp ASC
    """).fetchall()

    bursts = []
    current_burst = []

    for row in rows:
        if not current_burst:
            current_burst.append(row)
            continue

        prev_ts = current_burst[-1]["timestamp"]
        curr_ts = row["timestamp"]
        try:
            from datetime import datetime
            prev_dt = datetime.fromisoformat(prev_ts)
            curr_dt = datetime.fromisoformat(curr_ts)
            gap = abs((curr_dt - prev_dt).total_seconds())
        except Exception:
            gap = BURST_TIME_GAP_SECONDS + 1

        if gap <= BURST_TIME_GAP_SECONDS:
            current_burst.append(row)
        else:
            if len(current_burst) >= 2:
                bursts.append(current_burst)
            current_burst = [row]

    if len(current_burst) >= 2:
        bursts.append(current_burst)

    for burst in bursts:
        phash_valid = [(r["id"], r["phash"], r["aesthetic_score"] or 0)
                       for r in burst if r["phash"]]

        if len(phash_valid) < 2:
            continue

        valid = True
        for i in range(len(phash_valid) - 1):
            d = _phash_distance(phash_valid[i][1], phash_valid[i + 1][1])
            if d > BURST_PHASH_DISTANCE:
                valid = False
                break

        if not valid:
            continue

        phash_valid.sort(key=lambda x: x[2], reverse=True)
        cluster_id = f"burst_{burst[0]['id']}"

        for idx, (asset_id, _, _) in enumerate(phash_valid):
            if idx < BURST_HERO_COUNT:
                role = "hero"
            elif idx < BURST_HERO_COUNT + BURST_BACKUP_COUNT:
                role = "backup"
            else:
                role = "pruned"

            conn.execute("""
                UPDATE assets SET cluster_role=?, cluster_id=?
                WHERE id=?
            """, (role, cluster_id, asset_id))
        conn.commit()


def cluster_faces():
    conn = get_connection()
    rows = conn.execute("""
        SELECT f.id, f.embedding, f.asset_id, f.identity_name
        FROM faces f
        JOIN assets a ON f.asset_id = a.id
        WHERE a.status = 'analyzed'
    """).fetchall()

    embeddings = []
    face_ids = []
    for row in rows:
        if row["embedding"]:
            try:
                emb = np.frombuffer(row["embedding"], dtype=np.float32)
                if emb.shape[0] == 512:
                    embeddings.append(emb)
                    face_ids.append((row["id"], row["asset_id"], row["identity_name"]))
            except Exception:
                continue

    if len(embeddings) < 3:
        return

    from sklearn.cluster import DBSCAN
    X = np.array(embeddings)
    clustering = DBSCAN(eps=0.6, min_samples=3, metric="cosine").fit(X)

    cluster_map = defaultdict(list)
    for face_idx, label in enumerate(clustering.labels_):
        if label >= 0:
            cluster_map[int(label)].append(face_ids[face_idx])

    for cluster_label, members in cluster_map.items():
        if len(members) < 3:
            continue

        known_names = [m[2] for m in members if m[2] is not None]
        cluster_label_str = f"fc_{cluster_label}"

        conn.execute("""
            INSERT OR REPLACE INTO face_clusters
                (id, label, priority, face_count)
            VALUES (?, ?, ?, ?)
        """, (
            cluster_label_str,
            known_names[0] if known_names else None,
            1 if not known_names else None,
            len(members),
        ))
        conn.commit()
