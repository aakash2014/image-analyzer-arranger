# PhotoCurator — MVP Plan

## Philosophy

Build a **working end-to-end pipeline** with the minimum viable features. No UI, no video, no OCR. Just a Python CLI that scans a folder and produces a suggestion report. Once this works, we layer on features incrementally.

---

## MVP Scope (What's In / What's Out)

### ✅ In — Backend Python Engine Only
| Feature | How |
|---|---|
| Recursive folder scan (images only) | `scandir()`, filter by extension |
| Image preprocessing (resize to 640px) | Pillow |
| Blur detection | Laplacian variance |
| Aesthetic scoring | Simplified: use brightness/contrast/entropy as proxy (no NIMA model in MVP) |
| Face detection + cropping | Use `insightface` (RetinaFace) — auto-downloads model |
| Face embeddings | Use `insightface` (ArcFace) — auto-downloads model |
| Scene classification | Use CLIP via `sentence-transformers` or `transformers` |
| Junk probability | Heuristic: low res + no faces + blur + low aesthetic |
| Perceptual hashing | `imagehash` (pHash) for near-duplicate detection |
| SHA-256 hashing | `hashlib` |
| Burst clustering | Timestamp gap < 2s + pHash distance < 15 |
| Face clustering | Simple cosine similarity grouping (no FAISS in MVP — use sklearn `cosine_similarity` or brute force) |
| MemoryScore formula | Per README: FacePriority×0.4 + QualityScore×0.3 + SceneScore×0.2 - JunkPenalty×0.1 |
| Suggestions output | JSON report: Top Memories, Junk Candidates, Burst Pruning |
| SQLite database | Store assets, faces, suggestions |
| FastAPI REST API | Endpoints: `/scan`, `/scan/{id}`, `/suggestions`, `/summary` |

### ❌ Out of MVP
| Feature | Reason |
|---|---|
| Electron/React UI | Start with REST API + manual curl/browser |
| Video processing | Images only |
| OCR (EasyOCR) | Heavy, add later for screenshot detection |
| NIMA model (ONNX) | Use heuristic aesthetic proxy instead |
| FAISS | Use simple numpy/sklearn for MVP |
| Trip detection | Needs GPS + timeline analysis |
| Event detection | Needs face consistency analysis |
| Face labeling UI | Will use a simple script or manual DB update |
| Face merge / auto-match | Not needed until face labeling exists |
| Incremental rescan | Full scan each time for MVP |
| Settings | Hardcoded constants |
| Export CSV/JSON | JSON only for MVP |

---

## Project Structure (MVP)

```
image-analyzer-arranger/
├── README.md
├── MVP.md
├── requirements.txt
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Hardcoded settings
│   ├── database.py                # SQLite setup + models
│   ├── scanner.py                 # Recursive folder scan + hashing
│   ├── preprocess.py              # Image loading + resize
│   ├── image_pipeline.py          # Orchestrator
│   ├── face_engine.py             # RetinaFace + ArcFace via insightface
│   ├── scene_analyzer.py          # CLIP-based scene classification
│   ├── aesthetic.py               # Heuristic aesthetic scoring
│   ├── blur_detector.py           # Laplacian variance
│   ├── junk_classifier.py         # Heuristic junk probability
│   ├── hasher.py                  # SHA-256 + pHash
│   ├── clustering.py              # Burst + face clustering
│   ├── scorer.py                  # MemoryScore calculation
│   ├── suggestion_engine.py       # Category assignment
│   └── routers/
│       ├── scan.py                # POST /scan, GET /scan/{id}
│       ├── suggestions.py         # GET /suggestions
│       └── summary.py             # GET /summary
└── tests/
    ├── test_scanner.py
    ├── test_face_engine.py
    ├── test_clustering.py
    └── test_scorer.py
```

---

## Build Order

### Step 1 — Project Scaffold
- `requirements.txt` (fastapi, uvicorn, pillow, imagehash, insightface, onnxruntime, transformers, torch, scikit-learn, numpy)
- `config.py` with settings
- `database.py` with SQLite schema (assets, faces, suggestions tables)

### Step 2 — Ingestion
- `hasher.py` — SHA-256 + pHash
- `scanner.py` — walk folder, hash files, store in DB
- Test: scan a folder, verify DB entries

### Step 3 — Image Preprocessing
- `preprocess.py` — load image, auto-orient, resize to 640px max

### Step 4 — AI Pipeline (Image Intelligence)
- `blur_detector.py` — Laplacian variance
- `aesthetic.py` — brightness + contrast + entropy heuristic
- `face_engine.py` — insightface for detection + embedding
- `scene_analyzer.py` — CLIP scene tags
- `junk_classifier.py` — combine signals into junk_probability
- `image_pipeline.py` — orchestrate all of the above per image

### Step 5 — Clustering
- `clustering.py` — burst groups (timestamp + pHash) and face grouping (cosine similarity)

### Step 6 — Scoring & Suggestions
- `scorer.py` — MemoryScore formula
- `suggestion_engine.py` — assign categories based on thresholds

### Step 7 — REST API
- FastAPI app with scan/suggestions/summary endpoints
- Scan runs async in background thread, reports progress

### Step 8 — Verification
- Point at a test folder with known photos
- Run scan, inspect suggestion JSON
- Validate that junk/blurry/duplicates are flagged

---

## What a Working MVP Looks Like

```bash
# Start the API
python backend/main.py

# Start a scan
curl -X POST http://localhost:8765/scan -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/photos"}'

# Poll for progress
curl http://localhost:8765/scan/1

# Get suggestions when done
curl http://localhost:8765/suggestions

# Get summary
curl http://localhost:8765/summary
```

Output: a JSON report with categorized suggestions — Top Memories, Junk, Burst Pruning — each with file paths, confidence scores, and reasons.

---

## After MVP (Future Steps)

Once the MVP is stable, we add features in this order based on feedback:
1. OCR + screenshot detection (improve junk classifier)
2. NIMA model (replace heuristic aesthetic)
3. FAISS (replace brute-force face search, scale to 100k+ photos)
4. Video support (FFmpeg keyframing)
5. Trip + event detection
6. React frontend (Electron shell)
7. Incremental scanning
8. Face labeling UI
9. CSV/JSON export
10. Packaging
