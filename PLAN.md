# PhotoCurator — Full Implementation Plan

## Release Philosophy

Each phase is a **releasable, testable milestone**. Every phase builds on the last and delivers working software you can run and evaluate. No phase takes more than a few days of focused work.

---

## Release Cadence

| Phase | Name | Est. Days | What You Get |
|---|---|---|---|
| 1 | MVP Engine | 3-4 | Working backend: scan folder → AI analysis → suggestion JSON |
| 2 | Smarter AI | 2-3 | Real models replace heuristics: NIMA, OCR, better junk detection |
| 3 | Video Pipeline | 2-3 | Video support: keyframe extraction, aggregation, video suggestions |
| 4 | Face System | 2-3 | FAISS indexing, face labeling, auto-matching, merge |
| 5 | Trip & Events | 2-3 | Trip detection, event detection, travel highlights |
| 6 | Desktop UI | 4-5 | React frontend with Electron shell, full GUI |
| 7 | Scale & Polish | 2-3 | Incremental scanning, settings, export (CSV/JSON), packaging |
| **Total** | | **~18-24** | **Complete desktop app** |

---

## Phase 1: MVP Engine

**Goal:** A working Python backend that scans a folder of images and produces a JSON suggestion report. Everything runs via REST API on `localhost:8765`. No UI, no video, no real models — heuristics for aesthetic scoring.

### What's Built

| Module | Files | What It Does |
|---|---|---|
| **Scaffold** | `requirements.txt`, `config.py`, `database.py` | Project setup, SQLite schema, hardcoded settings |
| **Ingestion** | `scanner.py`, `hasher.py` | Recursive folder walk, SHA-256 + pHash, store in DB |
| **Preprocessing** | `preprocess.py` | Load image, auto-orient, resize to 640px, normalize |
| **Face Engine** | `face_engine.py` | insightface RetinaFace + ArcFace (auto-downloads models) |
| **Scene Analyzer** | `scene_analyzer.py` | CLIP via transformers — classify into scene categories |
| **Blur Detector** | `blur_detector.py` | Laplacian variance, threshold-based |
| **Aesthetic** | `aesthetic.py` | Heuristic: brightness + contrast + entropy (no model) |
| **Junk Classifier** | `junk_classifier.py` | Heuristic: low res + no faces + blur + low aesthetic |
| **Clustering** | `clustering.py` | Burst groups (timestamp + pHash), face groups (cosine sim) |
| **Scorer** | `scorer.py` | MemoryScore formula: Face×0.4 + Quality×0.3 + Scene×0.2 - Junk×0.1 |
| **Suggestions** | `suggestion_engine.py` | Assign categories: Top Memories, Junk, Burst Pruning |
| **API** | `routers/scan.py`, `routers/suggestions.py`, `routers/summary.py`, `main.py` | FastAPI endpoints, async background scan |
| **Tests** | `tests/` | Tests for scanner, face, clustering, scorer |

### How to Test Phase 1

```bash
# Install
pip install -r requirements.txt

# Start server
python backend/main.py

# Scan a test folder
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/test/photos"}'

# Get suggestions
curl http://localhost:8765/suggestions

# Get summary
curl http://localhost:8765/summary
```

### Definition of Done
- [x] Backend starts and `/health` returns OK
- [x] Scan detects all images in a folder
- [x] SHA-256 and pHash computed for each image
- [x] Blur detection correctly identifies blurry images
- [x] Face detection finds faces in group/portrait photos
- [x] CLIP scene classification runs (landscape, food, portrait, etc.)
- [x] Burst clustering groups near-identical photos
- [x] MemoryScore computed per image
- [x] Suggestions categorized: Top Memories, Junk, Burst Pruning
- [x] Suggestions endpoint returns valid JSON with file paths + reasons
- [x] Summary endpoint returns counts per category

### Edge Cases Handled
- Empty folder → returns empty results, no crash
- Unsupported file types → silently skipped
- Corrupted images → logged as error, skipped gracefully
- No faces in any photo → MemoryScore uses 0 for face component
- All photos are junk → Junk category contains everything
- Single photo → no burst clusters, single Top Memory candidate
- Photos with no EXIF → uses file modification time

---

## Phase 2: Smarter AI

**Goal:** Replace heuristic aesthetic scoring with a real neural model (NIMA). Add OCR-based screenshot detection and a proper junk classifier. Improve face matching accuracy.

### What's Added

| Module | Change |
|---|---|
| **NIMA** (new) | `aesthetic.py` rewritten — ONNX NIMA model for true aesthetic scoring (1-10) |
| **OCR** (new) | `ocr.py` — EasyOCR for text detection in images. Detects screenshots, documents, WhatsApp forwards with text overlay |
| **Junk Classifier** | `junk_classifier.py` rewritten — combines NIMA score, OCR text coverage, blur, resolution, path patterns into weighted probability formula per README |
| **Face Matching** | `face_engine.py` — add cosine similarity threshold logic (0.85 auto-match, 0.7-0.85 flag for review) |
| **Face Priority** | `face_engine.py` — assign default priorities (unknown=1, known=5/7/10 based on user labels) |

### Model Downloads

| Model | Source | Size | Download |
|---|---|---|---|
| NIMA | ONNX model zoo or custom export | ~5MB | Auto-download on first run or bundled |
| EasyOCR | PyPI (`easyocr`) | ~50MB (models) | Auto-downloads on first use |

### How to Test Phase 2

```bash
# Run the same scan on the same test folder
# Compare before/after:
#   - Aesthetic scores should now be more accurate (1-10)
#   - Junk detection should catch screenshots it missed before
#   - Face auto-matching should label known faces

# Test screenshot detection specifically:
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/screenshots"}'
# Expect >90% of screenshots flagged as junk
```

### Definition of Done
- [ ] NIMA scores available for every image (1-10 normalized to 0-1)
- [ ] OCR detects text-heavy images as screenshot candidates
- [ ] Junk probability uses all signals (NIMA, OCR, blur, resolution, path)
- [ ] Face auto-matching at >0.85 cosine similarity
- [ ] Junk detection accuracy >80% on test set
- [ ] Performance: <1s per image on modern CPU

---

## Phase 3: Video Pipeline

**Goal:** Add video processing. Extract keyframes via FFmpeg, run image pipeline on keyframes, aggregate results, generate video-level suggestions.

### What's Added

| Module | What It Does |
|---|---|
| `video_pipeline.py` | Orchestrates video processing: keyframe extraction → keyframe analysis → aggregation |
| `ffmpeg_utils.py` | Wrapper around FFmpeg subprocess calls. Extract keyframes via scene detection filter, probe metadata via FFprobe |
| `keyframe_selector.py` | Picks best representative frame (highest aesthetic + face presence + central position) |
| `video_aggregator.py` | Aggregates per-keyframe results: max face priority, union of identities, max NIMA, mode scene, min blur |

### Database Changes

| Table | New Column |
|---|---|
| `assets` | `duration` (float, seconds) |
| `assets` | `codec` (text) |
| `assets` | `bitrate` (text) |
| `assets` | `fps` (text) |
| `assets` | `best_thumbnail_path` (text) |
| `assets` | `video_score` (float) |
| `assets` | `suggested_category` (text) |

### How to Test Phase 3

```bash
# Place a mix of photos and videos in test folder
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/mixed"}'  # includes .mp4, .mov, .avi

# Check videos appear in suggestions
curl http://localhost:8765/suggestions | jq '.videos | length'

# Verify keyframe extraction
ls /tmp/photocurator/keyframes/
```

### Prerequisites
- FFmpeg installed on system (`apt install ffmpeg` or `brew install ffmpeg`)
- Configurable path to ffmpeg binary

### Definition of Done
- [ ] FFmpeg keyframe extraction works (scene threshold 0.4, max 50 keyframes)
- [ ] Each keyframe runs through image pipeline (faces, scene, aesthetic, blur)
- [ ] Video-level aggregation produces correct max/union/mode per metric
- [ ] Videos appear in suggestions with `type: video`
- [ ] Video duration, codec, resolution, FPS stored in DB
- [ ] Thumbnail selected and stored for UI preview
- [ ] Videos without faces but high aesthetic → Travel/Landscape candidates

---

## Phase 4: Face System

**Goal:** Replace brute-force face matching with FAISS. Add face labeling, known face management, auto-matching, and face merging.

### What's Added

| Module | What It Does |
|---|---|
| `faiss_manager.py` | FAISS index wrapper: load/create, add embeddings, search, save to disk |
| `face_clustering.py` | DBSCAN clustering on all face embeddings. Generate face clusters |
| `face_labeler.py` | CLI or API endpoint to label face clusters with name + priority |
| `face_merger.py` | Periodically re-cluster unknowns, merge overlapping clusters |
| `face_router.py` (new API) | `GET /faces` (list clusters), `PUT /faces/{id}` (label), `POST /faces/merge` |

### Database Changes

| Table | Changes |
|---|---|
| `faces` | New: `name`, `priority`, `embedding_count`, `cluster_id`, `is_known` |
| `face_clusters` | New table: `id`, `label`, `priority`, `face_count`, `centroid_embedding` |
| `assets` | Add index on `face_ids` for faster queries |

### FAISS Indexes

| Index | File | Dimension | Purpose |
|---|---|---|---|
| `face_embeddings.faiss` | Stored in app data dir | 512 | ArcFace face embeddings |
| `face_id_map.faiss` | Stored alongside | n/a | Maps FAISS vector IDs to SQLite face IDs |

### How to Test Phase 4

```bash
# After a scan, list face clusters
curl http://localhost:8765/faces

# Label a face cluster
curl -X PUT http://localhost:8765/faces/1 \
  -H 'Content-Type: application/json' \
  -d '{"name": "Mom", "priority": 10}'

# Re-run scan — new photos of Mom should auto-match
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/new_photos"}'

# Verify auto-matching
curl http://localhost:8765/suggestions | jq '.top_memories[0].faces'
# Expected: ["Mom"]
```

### Definition of Done
- [ ] FAISS index created and persisted to disk
- [ ] DBSCAN clustering groups similar faces (eps=0.6, min_samples=3)
- [ ] Face clusters returned via `/faces` endpoint
- [ ] Labeling a cluster (name + priority) stored in DB
- [ ] Auto-matching works: new face with >0.85 similarity gets label
- [ ] Possible matches (0.7-0.85) flagged for review
- [ ] Face merge: re-clustering unknowns merges overlapping clusters
- [ ] Performance: FAISS search <10ms for 100k embeddings
- [ ] Performance: FAISS index save/load <1s

---

## Phase 5: Trip & Events

**Goal:** Detect trips (2-14 day photo clusters with GPS or scene signals) and events (1-2 day high-density gatherings with faces).

### What's Added

| Module | What It Does |
|---|---|
| `trip_detector.py` | Implements README algorithm: date clustering + GPS variance + scene content. Produces trip objects with name, dates, locations, score |
| `event_detector.py` | Implements README algorithm: high photo density + face diversity + face consistency + time span. Produces event objects |
| `reverse_geo.py` | Local reverse geocoding lookup (city-level from GPS coordinates) — uses a bundled small dataset or offline library |
| `trip_router.py` (new API) | `GET /trips` (list trips), `PUT /trips/{id}` (rename trip) |

### Database Changes

| Table | Changes |
|---|---|
| `trips` | New table: `id`, `name`, `start_date`, `end_date`, `photo_count`, `locations_visited`, `family_members`, `average_quality`, `memory_score`, `trip_score`, `gps_center_lat`, `gps_center_lon` |
| `events` | New table: `id`, `name`, `date`, `photo_count`, `face_count`, `face_set`, `scene_variety`, `event_score` |
| `assets` | Add `trip_id` (FK), `event_id` (FK) columns |

### How to Test Phase 5

```bash
# Scan a folder with vacation photos (different dates, GPS-tagged)
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/vacation_photos"}'

# Check detected trips
curl http://localhost:8765/trips
# Expected: ["Trip to Bali (Jun 12-18, 312 photos)"]

# Rename a trip
curl -X PUT http://localhost:8765/trips/1 \
  -H 'Content-Type: application/json' \
  -d '{"name": "Summer Vacation 2024"}'

# Verify travel highlights in suggestions
curl http://localhost:8765/suggestions | jq '.travel_highlights | length'
```

### Test Scenarios

| Scenario | Expected Result |
|---|---|
| 50 photos from same day, no GPS | No trip (needs 2+ days) |
| 200 photos over 7 days, no GPS | Trip detected via date density + scene content |
| 500 photos over 5 days, GPS-tagged | Trip detected, named via reverse geocode |
| 100 photos in 2 hours (birthday party) | Event detected (high face density + time span) |
| Screenshots over 3 days | Not a trip (low scene scores for travel categories) |

### Definition of Done
- [ ] Trip detection algorithm matches README spec (3 signals, weighted)
- [ ] Event detection algorithm matches README spec (face density + consistency + time span)
- [ ] Trips returned via `/trips` endpoint with metadata
- [ ] Travel Highlights suggestion category populated from trip members
- [ ] Reverse geocoding works for known cities
- [ ] Trips without GPS named "Trip — {month} {year}"
- [ ] User can rename trips via API

---

## Phase 6: Desktop UI

**Goal:** Build a React frontend with Electron shell. The UI provides the full user experience: scan progress, dashboard, suggestions browsing, face labeling, trip view, and export.

### Tech Stack

| Layer | Technology |
|---|---|
| Frontend framework | React 18 + TypeScript |
| Build tool | Vite |
| UI components | Material UI or shadcn/ui |
| State management | React Query (TanStack Query) for server state |
| Routing | React Router v6 |
| Charts | Recharts (dashboard) |
| Desktop shell | Electron (main process) |
| IPC | HTTP REST to localhost:8765 (no IPC needed, simple fetch) |
| Packaging | electron-builder |

### Pages & Routes

| Route | Page | Description |
|---|---|---|
| `/` | Welcome | Folder picker + start scan button |
| `/scan/:id` | Scan Progress | Progress bar, phase indicator, cancel button |
| `/dashboard` | Dashboard | Summary stats, category breakdown, trip list, face stats |
| `/suggestions/:category` | Suggestions | Grid view of suggestions with action buttons |
| `/faces` | Face Labeling | Face cluster grid with name/priority input |
| `/trips` | Trips | Trip list with details and highlights |
| `/settings` | Settings | Configurable thresholds, paths, model selection |
| `/export` | Export | CSV/JSON download, summary report |

### Dashboard Layout (per README spec)

```
┌─────────────────────────────────────────────────────────┐
│  📊 Summary — C:\Photos\ (34,892 assets)               │
│                                                         │
│  ⭐ Top Memories         143 photos (0.4%)              │
│  👨‍👩‍👧 Family Priority     2,341 photos (6.7%)            │
│  🌍 Travel Highlights    4,212 photos (12.1%)            │
│  📸 Burst Pruning        1,876 photos (5.4%)            │
│  🗑 Junk Candidates      8,943 photos (25.6%)            │
│  ❓ Needs Review         17,377 photos (49.8%)           │
│                                                         │
│  🏆 12 Trips Detected                                   │
│  👥 47 Unique Faces (8 known, 39 unknown)              │
│  🎬 234 Videos Processed                                │
│                                                         │
│  Estimated reclaimable space: 8.2 GB                    │
└─────────────────────────────────────────────────────────┘
```

### Electron Main Process

| Feature | Implementation |
|---|---|
| Spawn Python backend | `child_process.spawn("python", ["backend/main.py"])` |
| Health monitoring | Periodic `GET /health`, restart on failure |
| Folder picker | `dialog.showOpenDialog` with directory option |
| App lifecycle | Kill Python on quit, handle crashes |
| Native menus | File, Edit, View, Help menus |

### How to Test Phase 6

```bash
# Start the full app
cd frontend && npm run dev    # React dev server
cd electron && npm run start  # Electron shell

# Or build for distribution
cd frontend && npm run build
cd electron && npm run dist
```

### Definition of Done
- [ ] Welcome page with folder picker
- [ ] Scan progress page shows real-time progress (polling `/scan/{id}`)
- [ ] Dashboard displays correct stats from `/summary`
- [ ] Suggestions page shows categorized thumbnails with Keep/Delete/Review buttons
- [ ] Face labeling page shows clusters side by side
- [ ] Trip view shows trip cards with highlight photos
- [ ] Settings page with editable config values
- [ ] Export page generates and downloads CSV/JSON
- [ ] Electron shell spawns Python backend on startup
- [ ] Electron kills Python on app close
- [ ] Error handling: show error page when backend unreachable

---

## Phase 7: Scale & Polish

**Goal:** Production-ready features: incremental scanning, configurable settings, multiple export formats, packaging for distribution.

### What's Added

| Feature | What It Does |
|---|---|
| **Incremental Scanning** | `scanner.py` compares file paths + modification times against DB. Only process new/modified files. Remove deleted files from DB |
| **Settings** | `config.py` becomes dynamic — JSON config file in app data dir. API endpoints to read/write settings |
| **User Feedback** | `PUT /feedback` endpoint — store user accept/dismiss for each suggestion. Improve confidence based on feedback |
| **Export CSV** | CSV export with all fields per README spec |
| **Export JSON** | JSON export with full asset metadata per README spec |
| **Export Summary** | Human-readable text report |
| **Packaging** | `electron-builder` config for Windows (NSIS), macOS (DMG), Linux (AppImage) |
| **Model Cache** | Pre-download models on first launch, store in app data dir, verify integrity |

### Settings

| Setting | Default | Description |
|---|---|---|
| `max_image_dimension` | 640 | Max pixels on longest edge for AI processing |
| `face_confidence_threshold` | 0.5 | Minimum confidence for face detection |
| `face_auto_match_threshold` | 0.85 | Cosine similarity for auto-labeling |
| `burst_time_gap` | 2 | Seconds between burst photos |
| `burst_phash_distance` | 15 | Max Hamming distance for burst |
| `junk_probability_threshold` | 0.7 | Threshold for junk category |
| `top_memory_score_threshold` | 0.85 | Threshold for Top Memories |
| `scene_change_threshold` | 0.4 | FFmpeg scene detection sensitivity |
| `max_keyframes_per_video` | 50 | Maximum keyframes to extract |
| `enable_ocr` | true | Enable EasyOCR for screenshot detection |
| `model_cache_dir` | `./models` | Directory for downloaded ONNX models |
| `db_path` | `./photocurator.db` | SQLite database path |
| `logs_dir` | `./logs` | Log file directory |

### Packaging

| Platform | Format | electron-builder target |
|---|---|---|
| Windows | NSIS installer (`.exe`) | `nsis` |
| macOS | DMG (`.dmg`) | `dmg` |
| Linux | AppImage (`.AppImage`) | `appimage` |

### How to Test Phase 7

```bash
# Test incremental scan
curl -X POST http://localhost:8765/scan \
  -H 'Content-Type: application/json' \
  -d '{"folder": "/path/to/photos"}'
# First scan: processes all

# Add 5 new photos to the folder
# Run scan again
# Second scan: processes only 5 new files, skips existing

# Test export
curl http://localhost:8765/export?format=csv -o report.csv
curl http://localhost:8765/export?format=json -o report.json

# Test settings
curl http://localhost:8765/settings
curl -X PUT http://localhost:8765/settings \
  -H 'Content-Type: application/json' \
  -d '{"junk_probability_threshold": 0.8}'

# Build package
cd electron && npm run dist
```

### Definition of Done
- [ ] Incremental scan: second run is >10x faster than first
- [ ] Deleted files are removed from DB on scan
- [ ] Settings API returns and updates all config values
- [ ] CSV export matches README spec (file_path, type, category, suggested_action, confidence, reason)
- [ ] JSON export matches README spec (export_date, source_folder, total_assets, assets[])
- [ ] Summary export is a readable text report
- [ ] User feedback endpoint stores accept/dismiss decisions
- [ ] Electron app packages successfully for at least Linux (current platform)
- [ ] First-run experience: models downloaded and cached
- [ ] App handles missing models gracefully (error message, retry option)

---

## Complete File Tree (Final)

```
image-analyzer-arranger/
├── README.md
├── PLAN.md
├── MVP.md
├── LICENSE
├── .gitignore
├── .git-creds                      # Local credential store (gitignored)
│
├── backend/
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Settings (hardcoded → dynamic in P7)
│   ├── database.py                 # SQLite setup + models
│   ├── scanner.py                  # Recursive folder scan
│   ├── hasher.py                   # SHA-256 + pHash
│   ├── preprocess.py               # Image loading + resize
│   ├── image_pipeline.py           # Image AI orchestration
│   ├── face_engine.py              # RetinaFace + ArcFace (insightface)
│   ├── scene_analyzer.py           # CLIP scene classification
│   ├── aesthetic.py                # Aesthetic scoring (heuristic → NIMA in P2)
│   ├── blur_detector.py            # Laplacian variance
│   ├── ocr.py                      # EasyOCR (P2)
│   ├── junk_classifier.py          # Junk probability (heuristic → weighted in P2)
│   ├── faiss_manager.py            # FAISS indexing (P4)
│   ├── face_clustering.py          # DBSCAN face clustering (P4)
│   ├── face_labeler.py             # Face naming + priority (P4)
│   ├── face_merger.py              # Unknown face merge (P4)
│   ├── video_pipeline.py           # Video orchestration (P3)
│   ├── ffmpeg_utils.py             # FFmpeg wrapper (P3)
│   ├── keyframe_selector.py        # Best keyframe selection (P3)
│   ├── video_aggregator.py         # Keyframe aggregation (P3)
│   ├── clustering.py               # Burst clustering
│   ├── trip_detector.py            # Trip detection (P5)
│   ├── event_detector.py           # Event detection (P5)
│   ├── reverse_geo.py              # GPS → city name (P5)
│   ├── scorer.py                   # MemoryScore calculation
│   ├── suggestion_engine.py         # Category assignment
│   └── routers/
│       ├── scan.py                 # POST /scan, GET /scan/{id}
│       ├── suggestions.py          # GET /suggestions
│       ├── summary.py              # GET /summary
│       ├── faces.py                # GET/PUT /faces (P4)
│       ├── trips.py                # GET/PUT /trips (P5)
│       ├── settings.py             # GET/PUT /settings (P7)
│       ├── export.py               # GET /export (P7)
│       └── feedback.py             # PUT /feedback (P7)
│
├── frontend/                       # React app (P6)
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/
│       │   └── client.ts           # HTTP client to backend
│       ├── pages/
│       │   ├── Welcome.tsx
│       │   ├── ScanProgress.tsx
│       │   ├── Dashboard.tsx
│       │   ├── Suggestions.tsx
│       │   ├── FaceLabeling.tsx
│       │   ├── Trips.tsx
│       │   ├── Settings.tsx
│       │   └── Export.tsx
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── AssetCard.tsx
│       │   ├── FaceCluster.tsx
│       │   ├── TripCard.tsx
│       │   ├── ProgressBar.tsx
│       │   └── CategoryBadge.tsx
│       └── styles/
│           └── globals.css
│
├── electron/                       # Electron shell (P6)
│   ├── package.json
│   ├── main.ts                     # Electron main process
│   ├── preload.ts                  # Context bridge
│   └── electron-builder.yml        # Packaging config (P7)
│
├── models/                         # Downloaded ONNX models (cached)
│   └── .gitkeep
│
├── tests/
│   ├── test_scanner.py
│   ├── test_face_engine.py
│   ├── test_clustering.py
│   ├── test_scorer.py
│   ├── test_nima.py                # P2
│   ├── test_ocr.py                 # P2
│   ├── test_video_pipeline.py      # P3
│   ├── test_faiss_manager.py       # P4
│   ├── test_trip_detector.py       # P5
│   └── test_event_detector.py      # P5
│
└── test_data/                      # Sample photos for testing
    └── .gitkeep
```

---

## Dependency Tree (Backend)

```
backend/main.py
  ├── routers/scan.py
  │     ├── scanner.py → hasher.py, database.py
  │     └── image_pipeline.py
  │           ├── preprocess.py
  │           ├── face_engine.py
  │           ├── scene_analyzer.py
  │           ├── aesthetic.py (→ NIMA P2)
  │           ├── blur_detector.py
  │           └── junk_classifier.py (→ ocr.py P2)
  ├── routers/suggestions.py → suggestion_engine.py → scorer.py, database.py
  ├── routers/summary.py → database.py
  ├── routers/faces.py (P4) → face_clustering.py → faiss_manager.py, database.py
  ├── routers/trips.py (P5) → trip_detector.py, event_detector.py, database.py
  ├── routers/settings.py (P7) → config.py
  ├── routers/export.py (P7) → suggestion_engine.py, database.py
  └── routers/feedback.py (P7) → database.py
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| ONNX models fail on CPU | Low | High | Fallback to heuristics; log error, continue processing |
| insightface model download fails | Medium | Medium | Bundle model or provide manual download instructions |
| FFmpeg not installed | Medium | High (P3) | Check on startup, show clear error with install instructions |
| EasyOCR too slow on CPU | Medium | Medium (P2) | Make OCR optional (config toggle), batch processing |
| CLIP model too large (>2GB) | Medium | Medium | Use smaller variant (e.g., `openai/clip-vit-base-patch32` is ~600MB) |
| Memory exhaustion on large folders | Low | High | Process images in batches (configurable batch size), release memory between batches |
| Face clustering quality poor | Medium | Medium | Tune DBSCAN params; add user override option |
| Electron packaging fails | Low | Medium | Start with platform-specific fixes; test on target OS early |
| SQLite contention during scan | Low | Low | Use WAL mode, single writer, retry on locked |
| GPU not available | High | Medium | All models designed for CPU; no GPU dependency |

---

## How Each Phase Is Tested

| Phase | Test Type | What We Verify |
|---|---|---|
| 1 | Manual + unit tests | Curl API endpoints, inspect JSON output. Unit tests for key functions |
| 2 | Side-by-side comparison | Scan same folder with old heuristic vs new NIMA/OCR — compare suggestion quality |
| 3 | Manual + video samples | Scan folder with mixed media. Verify keyframes extracted, videos in suggestions |
| 4 | Manual + integration | Label faces, add new photos, verify auto-matching. Check FAISS index persistence |
| 5 | Manual + curated datasets | Feed known trip/event photo sets, verify correct detection |
| 6 | Manual + UI testing | Click through every page. Test Electron lifecycle (start, crash, stop) |
| 7 | Manual + regression | Incremental scan 2x faster. Export produces valid files. Package installs cleanly |
