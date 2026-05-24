import numpy as np

from backend.database import get_connection
from backend.preprocess import load_and_preprocess
from backend.face_engine import detect_faces, match_faces_to_known
from backend.scene_analyzer import analyze_scene
from backend.aesthetic import score_aesthetic
from backend.blur_detector import detect_blur
from backend.junk_classifier import classify_junk


def process_image(asset_id: int, file_path: str, width: int | None, height: int | None):
    image_tensor = load_and_preprocess(file_path)
    if image_tensor is None:
        return

    faces = detect_faces(image_tensor)
    face_count = len(faces)

    embeddings = [f["embedding"] for f in faces]
    face_matches = match_faces_to_known(embeddings)

    max_face_priority = 0
    face_ids = []
    for i, face in enumerate(faces):
        match = face_matches[i] if i < len(face_matches) else {}
        conn = get_connection()
        cursor = conn.execute("""
            INSERT INTO faces
                (asset_id, embedding, identity_name, identity_priority,
                 confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                 landmark_left_eye_x, landmark_left_eye_y,
                 landmark_right_eye_x, landmark_right_eye_y)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            asset_id,
            face["embedding"].tobytes() if face["embedding"] is not None else None,
            match.get("identity"),
            match.get("priority", 1),
            match.get("confidence", 0.0),
            face["bbox"][0], face["bbox"][1],
            face["bbox"][2], face["bbox"][3],
            face["landmarks"][0][0] if face.get("landmarks") is not None else None,
            face["landmarks"][0][1] if face.get("landmarks") is not None else None,
            face["landmarks"][1][0] if face.get("landmarks") is not None else None,
            face["landmarks"][1][1] if face.get("landmarks") is not None else None,
        ))
        face_id = cursor.lastrowid
        face_ids.append(str(face_id))

        priority = match.get("priority", 1) if match else 1
        if priority > max_face_priority:
            max_face_priority = priority

    scene_category, scene_scores = analyze_scene(image_tensor)
    aesthetic = score_aesthetic(image_tensor)
    blur = detect_blur(image_tensor)
    junk_prob = classify_junk(file_path, width, height, face_count, aesthetic, blur)

    conn = get_connection()
    conn.execute("""
        UPDATE assets SET
            face_count = ?,
            face_ids = ?,
            max_face_priority = ?,
            scene_category = ?,
            aesthetic_score = ?,
            blur_score = ?,
            junk_probability = ?,
            status = 'analyzed'
        WHERE id = ?
    """, (
        face_count,
        ",".join(face_ids) if face_ids else None,
        max_face_priority,
        scene_category,
        aesthetic,
        blur,
        junk_prob,
        asset_id,
    ))
    conn.commit()
