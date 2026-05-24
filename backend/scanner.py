import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from PIL import Image
from PIL.ExifTags import TAGS

from backend.config import SUPPORTED_EXTENSIONS, LOW_RESOLUTION_THRESHOLD
from backend.database import get_connection
from backend.hasher import sha256_hash, phash_image


def scan_folder(folder: str, scan_job_id: int) -> list[dict]:
    conn = get_connection()
    folder = os.path.abspath(folder)
    conn.execute("UPDATE scan_jobs SET status='scanning', current_phase='scanning' WHERE id=?", (scan_job_id,))
    conn.commit()

    assets = []
    all_files = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                all_files.append(os.path.join(root, fname))

    conn.execute("UPDATE scan_jobs SET total_files=? WHERE id=?", (len(all_files), scan_job_id))
    conn.commit()

    for idx, file_path in enumerate(all_files):
        try:
            stat = os.stat(file_path)
            file_size = stat.st_size
            ext = os.path.splitext(file_path)[1].lower()
            file_type = "image"

            sha256 = sha256_hash(file_path)
            phash = phash_image(file_path)

            width, height = get_image_dimensions(file_path)
            timestamp = get_image_timestamp(file_path, stat)
            gps_lat, gps_lon = get_gps_coords(file_path)
            camera_model = get_camera_model(file_path)

            conn.execute("""
                INSERT OR REPLACE INTO assets
                    (file_path, file_name, file_size, file_type,
                     width, height, sha256, phash, timestamp,
                     gps_lat, gps_lon, camera_model, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                file_path, os.path.basename(file_path), file_size, file_type,
                width, height, sha256, phash, timestamp,
                gps_lat, gps_lon, camera_model,
            ))

            assets.append({
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "sha256": sha256,
                "phash": phash,
            })

            conn.execute("UPDATE scan_jobs SET processed_files=? WHERE id=?",
                         (idx + 1, scan_job_id))
            conn.commit()

        except Exception as e:
            print(f"Error scanning {file_path}: {e}")
            continue

    conn.execute("UPDATE scan_jobs SET status='scanned', current_phase='analyzing' WHERE id=?", (scan_job_id,))
    conn.commit()
    return assets


def get_image_dimensions(file_path: str) -> tuple[Optional[int], Optional[int]]:
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None, None


def get_image_timestamp(file_path: str, stat: os.stat_result) -> str:
    try:
        with Image.open(file_path) as img:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "DateTimeOriginal" or tag == "DateTime":
                        if isinstance(value, str):
                            try:
                                dt = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
                                return dt.isoformat()
                            except ValueError:
                                pass
    except Exception:
        pass
    return datetime.fromtimestamp(stat.st_mtime).isoformat()


def get_gps_coords(file_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        with Image.open(file_path) as img:
            exif = img._getexif()
            if not exif:
                return None, None
            gps_ifd = {}
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == "GPSInfo":
                    gps_ifd = value
                    break
            if not gps_ifd:
                return None, None

            def dms_to_decimal(dms, ref):
                if not dms:
                    return None
                degrees = float(dms[0])
                minutes = float(dms[1])
                seconds = float(dms[2])
                decimal = degrees + minutes / 60.0 + seconds / 3600.0
                if ref in ("S", "W"):
                    decimal = -decimal
                return decimal

            lat = dms_to_decimal(gps_ifd.get(2), gps_ifd.get(3, "N"))
            lon = dms_to_decimal(gps_ifd.get(4), gps_ifd.get(1, "E"))
            return lat, lon
    except Exception:
        return None, None


def get_camera_model(file_path: str) -> Optional[str]:
    try:
        with Image.open(file_path) as img:
            exif = img._getexif()
            if exif:
                for tag_id, value in exif.items():
                    tag = TAGS.get(tag_id, tag_id)
                    if tag == "Model":
                        return str(value)
    except Exception:
        pass
    return None
