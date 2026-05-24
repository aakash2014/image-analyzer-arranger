# PhotoCurator

**AI-Powered Local Memory Curator — Suggestion-Only Mode**

A desktop application that scans your photo and video folders, uses AI to analyze and sort everything, then **suggests** what to keep, what to prune, and what's junk — without ever touching your original files.

> **Phase 1:** Suggestion-only mode. No files are moved, renamed, or deleted.
> Everything is metadata-only. You review suggestions and manually act on them.

---

## Table of Contents

- [The Problem](#the-problem)
- [What PhotoCurator Does](#what-photocurator-does)
- [System Architecture](#system-architecture)
- [Processing Pipeline (Step by Step)](#processing-pipeline-step-by-step)
  - [Phase 1: Ingestion](#phase-1-ingestion)
  - [Phase 2: Image Intelligence](#phase-2-image-intelligence)
  - [Phase 3: Video Intelligence](#phase-3-video-intelligence)
  - [Phase 4: Clustering](#phase-4-clustering)
  - [Phase 5: Scoring & Suggestions](#phase-5-scoring--suggestions)
  - [Phase 6: User Review & Export](#phase-6-user-review--export)
- [Suggestion Categories](#suggestion-categories)
- [Face Recognition System](#face-recognition-system)
- [Trip & Event Detection](#trip--event-detection)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Packaging & Distribution](#packaging--distribution)
- [Safety & Privacy](#safety--privacy)
- [Build & Development](#build--development)
- [FAQ](#faq)

---

## The Problem

The average person has **thousands to hundreds of thousands** of photos and videos scattered across their hard drives, external disks, and phones. Over years of accumulation, this creates a mess:

- **Duplicates** — the same photo saved in multiple folders
- **Burst sequences** — 30 nearly identical shots of the same moment
- **Screenshots** — thousands of random screen captures
- **WhatsApp forwards** — low-quality images from messaging apps
- **Blurry photos** — accidental shots that should never have been kept
- **Memes and junk** — images that have no personal value
- **Unknown faces** — photos of strangers that add no memory value

Manually sorting through 50,000 photos to find the 500 that matter is impossible. Existing tools either:
- **Google Photos / Apple Photos** — work in the cloud, require upload, privacy concerns
- **PhotoPrism / Immich** — self-hosted but require Docker, server setup, complex
- **Manual sorting** — takes weeks, nobody does it

PhotoCurator fills the gap: **a single desktop app, runs locally, no cloud, no Docker, just AI-powered suggestions.**

---

## What PhotoCurator Does

### In One Sentence
Scan any folder of photos/videos, AI analyzes everything, and the app shows you clear suggestions of what to keep and what to delete — without touching a single file.

### What It Handles

| File Type | Supported Formats | What We Extract |
|---|---|---|
| **Images** | JPG, PNG, HEIC, WebP, BMP | Faces, scenes, quality score, blur, junk probability, EXIF metadata, GPS |
| **Videos** | MP4, MOV, AVI, MKV | Keyframes (via scene detection), face priority, scene category, quality aggregate, duration |

### What You Get Out

| Output | Description |
|---|---|
| ⭐ **Top Memories** | Best photos worth keeping forever |
| 👨‍👩‍👧 **Family Priority** | Photos containing family/close friends |
| 🌍 **Travel Highlights** | Best shots from detected trips |
| 📸 **Burst Pruning Candidates** | Near-identical photos — keep 1-2, delete rest |
| 🗑 **Junk Suggestions** | Screenshots, blurry, WhatsApp forwards, duplicates, memes |
| 📊 **Summary Dashboard** | Total count per category, trip timeline, face stats |
| 📁 **CSV/JSON Export** | Report with file paths, reasons, confidence scores |

### What It Does NOT Do (V1)

| Not in V1 | Reason |
|---|---|
| ❌ Automatic deletion | Safety first — user must review and decide |
| ❌ File renaming/moving | Users fear losing memories — trust is everything |
| ❌ Cloud sync/upload | Fully offline, privacy-first |
| ❌ Timeline builder | Out of MVP scope |
| ❌ Relationship graphs | Out of MVP scope |
| ❌ Adaptive learning | Future phase after user feedback collection |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PHOTOCURATOR DESKTOP APP                     │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    ELECTRON SHELL                            │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │              REACT FRONTEND (Renderer Process)        │  │   │
│  │  │                                                       │  │   │
│  │  │  Pages:     Welcome → ScanProgress → Dashboard       │  │   │
│  │  │                     → Suggestions → FaceLabeling     │  │   │
│  │  │                     → TripView → Settings → Export   │  │   │
│  │  │                                                       │  │   │
│  │  │  Communicates with Python backend via HTTP REST       │  │   │
│  │  │  (localhost:8765, no network access)                  │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  │                                                              │   │
│  │  ┌───────────────────────────────────────────────────────┐  │   │
│  │  │           ELECTRON MAIN PROCESS                      │  │   │
│  │  │  • Spawns Python backend as a child process           │  │   │
│  │  │  • Monitors health via heartbeat (GET /health)       │  │   │
│  │  │  • Kills Python on app close                          │  │   │
│  │  │  • Shows native OS dialogs (folder picker)            │  │   │
│  │  │  • Manages app lifecycle (startup, shutdown, crash)   │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │ HTTP REST (localhost:8765)                │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │                   PYTHON BACKEND (FastAPI)                   │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                    API ROUTERS                        │   │   │
│  │  │                                                       │   │   │
│  │  │  POST   /scan           Start a scan job              │   │   │
│  │  │  GET    /scan/{id}      Poll scan progress            │   │   │
│  │  │  GET    /faces          List all face clusters        │   │   │
│  │  │  PUT    /faces/{id}     Label a face identity         │   │   │
│  │  │  GET    /suggestions    Get suggestions (filterable)  │   │   │
│  │  │  GET    /summary        Dashboard statistics          │   │   │
│  │  │  GET    /trips          Detected trips                │   │   │
│  │  │  GET    /export         Download CSV/JSON report      │   │   │
│  │  │  PUT    /feedback       Record user accept/dismiss    │   │   │
│  │  │  GET    /settings       Current settings              │   │   │
│  │  │  PUT    /settings       Update settings               │   │   │
│  │  │  GET    /health         Health check + model status   │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                   CORE ENGINE                         │   │   │
│  │  │                                                       │   │   │
│  │  │  ┌──────────────┐  ┌──────────────────┐              │   │   │
│  │  │  │  INGESTION   │  │ IMAGE INTELLIGENCE│              │   │   │
│  │  │  │              │  │                  │              │   │   │
│  │  │  │ • scanner.py │  │ • RetinaFace     │              │   │   │
│  │  │  │ • hasher.py  │  │ • ArcFace        │              │   │   │
│  │  │  │ • metadata.py│  │ • CLIP           │              │   │   │
│  │  │  └──────────────┘  │ • NIMA           │              │   │   │
│  │  │                    │ • Blur detector  │              │   │   │
│  │  │  ┌──────────────┐  │ • Junk classifier│              │   │   │
│  │  │  │    VIDEO     │  └──────────────────┘              │   │   │
│  │  │  │              │                                     │   │   │
│  │  │  │ • FFmpeg     │  ┌──────────────────┐              │   │   │
│  │  │  │   keyframing │  │   CLUSTERING     │              │   │   │
│  │  │  │ • Aggregation│  │                  │              │   │   │
│  │  │  └──────────────┘  │ • FAISS (face)   │              │   │   │
│  │  │                    │ • Burst grouping │              │   │   │
│  │  │  ┌──────────────┐  │ • Trip detection │              │   │   │
│  │  │  │    SCORING   │  │ • Event detection│              │   │   │
│  │  │  │              │  └──────────────────┘              │   │   │
│  │  │  │ • MemoryScore│                                     │   │   │
│  │  │  │ • Suggestion │  ┌──────────────────┐              │   │   │
│  │  │  │   engine     │  │   FACE ENGINE    │              │   │   │
│  │  │  │ • Confidence │  │                  │              │   │   │
│  │  │  └──────────────┘  │ • Known list     │              │   │   │
│  │  │                    │ • Unknowns       │              │   │   │
│  │  │                    │ • Auto-merge     │              │   │   │
│  │  │                    └──────────────────┘              │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  │                                                              │   │
│  │  ┌──────────────────────────────────────────────────────┐   │   │
│  │  │                   DATA LAYER                         │   │   │
│  │  │                                                       │   │   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌───────────────┐  │   │   │
│  │  │  │   SQLite   │  │   FAISS    │  │   Model Cache │  │   │   │
│  │  │  │  (assets,  │  │  (face +   │  │  (ONNX files) │  │   │   │
│  │  │  │   faces,   │  │   scene    │  │               │  │   │   │
│  │  │  │  clusters) │  │ embeddings)│  │ ~300MB total  │  │   │   │
│  │  │  └────────────┘  └────────────┘  └───────────────┘  │   │   │
│  │  └──────────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Processing Pipeline (Step by Step)

Below is the complete data processing pipeline, from folder selection to final export. Each phase runs sequentially, and progress is reported to the frontend in real-time.

---

### Phase 1: Ingestion

**Purpose:** Find all files, check if they're new or already processed, extract basic metadata, and detect exact duplicates.

#### Step 1.1 — Recursive Folder Scan

The scanner walks the selected folder tree recursively and filters files by supported extensions:

```python
SUPPORTED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.heic', '.heif', '.webp', '.bmp',  # images
    '.mp4', '.mov', '.avi', '.mkv', '.m4v'                       # videos
}
```

**Incremental scanning:** On subsequent scans, the scanner compares file paths + modification timestamps against the database. Only new or modified files are queued for processing. Already-processed files are skipped entirely.

**Symlinks:** Ignored by default (configurable in settings).

#### Step 1.2 — Hashing (Duplicate Detection)

Two hashes are computed per file:

| Hash | Type | Purpose |
|---|---|---|
| **SHA-256** | Cryptographic hash | Find **exact** duplicates (same file content) |
| **Perceptual hash** (pHash) | Image fingerprint | Find **near-duplicates** (same photo, different resolution/compression) |

**SHA-256** is a cryptographic hash that produces the same output only for byte-identical files. Two files with the same SHA-256 are guaranteed duplicates.

**Perceptual hash** uses the `imagehash` library (DCT-based pHash) to generate a 64-bit fingerprint. Two images can be compared by **Hamming distance** — the number of differing bits:
- Distance 0 → identical image
- Distance 1-5 → near-identical (same photo, slightly different encoding)
- Distance 6-15 → similar scene (possible burst sequence candidate)
- Distance >15 → different images

For videos, only SHA-256 is computed (perceptual hashing is done on keyframes later).

#### Step 1.3 — Metadata Extraction

| Data | Source | Notes |
|---|---|---|
| Timestamp | EXIF (JPEG/TIFF) or file modification time | EXIF has priority when available |
| GPS latitude/longitude | EXIF | Only in images with location data |
| Camera model | EXIF | Make + model string |
| Resolution | Pillow (images) / FFprobe (videos) | e.g., "4032×3024" |
| File size | OS stat | In bytes |
| Orientation | EXIF | Auto-rotated during preview |
| Duration | FFprobe | Videos only, in seconds |
| Codec | FFprobe | Videos only |

#### Step 1.4 — Storage

All data is written to the `assets` table in SQLite with `status = 'pending'`.

**Progress contribution:** ~0-15%

---

### Phase 2: Image Intelligence

**Purpose:** For each image, run the complete AI pipeline to extract faces, scenes, quality scores, and junk probability.

All models run on **CPU** via **ONNX Runtime**. Images are resized to a maximum of 640px on the longest edge before inference to ensure reasonable speed.

#### Step 2.1 — Preprocessing

```
Input:  Raw image file (any resolution)
        │
        ▼
    1. Read with Pillow (auto-orient from EXIF)
        │
        ▼
    2. Convert to RGB (handle RGBA, grayscale)
        │
        ▼
    3. Resize: max dimension = 640px, maintain aspect ratio
        │
        ▼
    4. Normalize pixel values to [0, 1]
        │
        ▼
    5. Convert to CHW format (channels × height × width)
        │
        ▼
Output: np.array with shape (3, H, W), dtype=float32
```

This resizing step is critical for CPU performance. A 4000×3000 image (12MP) is reduced to ~640×480 pixels, which is sufficient for all downstream AI tasks.

#### Step 2.2 — Face Detection (RetinaFace)

**Model:** RetinaFace (ONNX, quantized)
**Input:** Preprocessed image (640px max)
**Output:** List of face bounding boxes with landmarks + confidence scores

RetinaFace detects faces at multiple scales. Key parameters:
- **Confidence threshold:** 0.5 (ignore low-confidence detections)
- **Maximum faces per image:** 50 (practical limit, extremely rare to exceed)
- **Landmark points:** 5 (left eye, right eye, nose, left mouth, right mouth)

For each detected face, the system:
1. Extracts the bounding box coordinates `[x1, y1, x2, y2]`
2. Uses landmarks to **align** the face (rotation correction based on eye positions)
3. Crops and resizes to 112×112 pixels for ArcFace input
4. Stores the face region in memory for embedding generation

**Performance:** ~100-200ms per image on modern CPU (single face).

#### Step 2.3 — Face Recognition / Embedding (ArcFace)

**Model:** ArcFace (ONNX, quantized)
**Input:** Aligned face crop (112×112)
**Output:** 512-dimensional embedding vector

Each detected face is converted to a **512-dimensional embedding vector** — a mathematical representation that captures the unique features of that face. These embeddings are the foundation of all face-related features:

- **Face matching:** Two faces are the same person if their embeddings are close (cosine similarity > 0.7)
- **Face clustering:** Similar embeddings group together to form person clusters
- **Face search:** Find all photos of a specific person by searching for similar embeddings

After generating the embedding, it is compared against the **known face list** (stored in FAISS):

```
New face embedding (512d)
        │
        ▼
FAISS index search → find nearest neighbor among known faces
        │
        ├── Similarity > 0.85 → Auto-match → assign known identity + priority
        ├── Similarity 0.7-0.85 → Flag for user review (possible match)
        └── Similarity < 0.7 → New unknown face → temporary ID
```

**Face priority system:**

| Priority | Category | Example | Score weight |
|---|---|---|---|
| 10 | Immediate family | Mom, Dad, Spouse, Child | Highest |
| 7 | Extended family | Grandparent, Sibling, Uncle | High |
| 5 | Friends | Close friends, Colleagues | Medium |
| 3 | Acquaintances | Neighbors, Distant friends | Low |
| 1 | Unknown / Stranger | Not yet identified | None |

Every suggestion involving a face uses the maximum face priority among all detected faces in that asset.

#### Step 2.4 — Scene Embedding (CLIP)

**Model:** CLIP (Contrastive Language-Image Pre-Training, ONNX)
**Input:** Preprocessed image (resized, normalized)
**Output:** 512-dimensional scene embedding vector + text similarity scores

CLIP generates a rich semantic understanding of the image content. Unlike traditional classifiers that could only output predefined classes, CLIP can understand images in an open-vocabulary way.

**Scene categories detected:**

| Category | Example CLIP Prompts |
|---|---|
| Landscape | "a landscape photo", "mountains", "beach", "sunset" |
| Indoor | "indoor photo", "room", "restaurant", "office" |
| Portrait | "a portrait photo", "selfie", "group of people" |
| Food | "food photography", "a meal", "plate of food" |
| City/Urban | "city street", "buildings", "urban landscape" |
| Nature | "forest", "garden", "flowers", "animals" |
| Event | "wedding", "birthday party", "celebration" |
| Travel | "tourist attraction", "landmark", "vacation" |
| Document | "screenshot of text", "document photo" |
| Art/Meme | "digital art", "meme", "funny image" |

Each category gets a similarity score (0-1). The highest-scoring category is stored as `scene_category`, and the full vector is stored in FAISS for scene-level clustering.

**Purpose in scoring:**
- Travel scenes → higher `SceneScore` (contributes to Travel Highlights)
- Document/screenshot → higher `junk_probability`
- Nature/landscape → medium `SceneScore`

#### Step 2.5 — Aesthetic Score (NIMA)

**Model:** NIMA (Neural Image Assessment, ONNX)
**Input:** Preprocessed image
**Output:** Mean score (1-10) + standard deviation

NIMA predicts how aesthetically pleasing a photo is, trained on millions of human-rated photos. It considers:
- Lighting and exposure
- Color harmony
- Composition and framing
- Sharpness and clarity
- Subject matter

The output is a **distribution** over 10 rating buckets. The mean gives the expected quality score, and the standard deviation indicates rating uncertainty.

| Mean Score | Meaning |
|---|---|
| 8.0-10.0 | Professional quality, highly aesthetic |
| 6.0-7.9 | Good quality, well-composed |
| 4.0-5.9 | Average snapshot quality |
| 2.0-3.9 | Poor quality, unappealing |
| 1.0-1.9 | Very low quality |

**Normalized score** (0-1) = `(mean_score - 1) / 9`

This becomes the `QualityScore` component of MemoryScore.

#### Step 2.6 — Blur Detection

**Method:** Laplacian variance (no ML model needed)

The Laplacian operator computes the second derivative of the image, measuring the amount of edges. A blurry image has fewer sharp edges, resulting in lower variance.

```
1. Convert image to grayscale
2. Apply Laplacian filter (kernel size = 3)
3. Compute variance of the result
4. Normalize by image dimensions
```

| Laplacian Variance | Result |
|---|---|
| > 100 | Sharp image |
| 50-100 | Slightly blurry (acceptable) |
| 20-50 | Moderately blurry |
| < 20 | Very blurry (junk candidate) |

Blurry images get a high `junk_probability` boost.

#### Step 2.7 — Junk Classifier

The junk detector combines **heuristic rules** with **AI signals** to identify low-value images:

| Rule | Method | Weight |
|---|---|---|
| **Low resolution** | Image width < 200px or height < 200px | High |
| **Screenshot detection** | OCR (EasyOCR) detects text covering >30% of image area | Medium |
| **WhatsApp pattern** | File path contains "WhatsApp", "IMG-20", or "WA-" prefixed names | High |
| **Aspect ratio check** | Exactly 9:16 or 16:9 with repetitive content → screenshot-like | Medium |
| **No faces + low aesthetic** | Face count = 0 AND NIMA score < 4.0 | Medium |
| **Solid color / gradient** | Color variance below threshold → blank screenshots | High |
| **Text-heavy** | OCR detects large amounts of text (documents, presentations) | Medium |
| **Meme detection** | Meme template patterns + text overlay | Low |

Each rule contributes to a cumulative `junk_probability` (0.0 - 1.0):

```
junk_probability = 1 - ∏(1 - weight_i) for each triggered rule
```

**Example:** A 320×240 WhatsApp image with no faces, low quality:
- Low resolution: triggered (weight 0.6)
- WhatsApp path: triggered (weight 0.7)
- No faces + low aesthetic: triggered (weight 0.4)
- **junk_probability = 1 - (0.4 × 0.3 × 0.6) = 0.928** → 93% confident junk

#### Step 2.8 — Image Intelligence Pipeline Orchestration

The `image_pipeline.py` orchestrator runs all the above steps for a single image:

```python
def process_image(asset_id, image_path):
    result = {}
    
    # Step 1: Preprocess
    image_tensor = preprocess(image_path)
    
    # Step 2: Face detection
    faces = detect_faces(image_tensor)
    result['face_count'] = len(faces)
    
    # Step 3: Face recognition (per face)
    for face in faces:
        embedding = encode_face(face['aligned_crop'])
        identity = match_face_to_known(embedding)
        face['identity'] = identity
        face['embedding'] = embedding
    
    # Step 4: Scene analysis
    scene_embedding, scene_scores = analyze_scene(image_tensor)
    result['scene_category'] = top_category(scene_scores)
    result['scene_embedding'] = scene_embedding
    
    # Step 5: Aesthetic score
    aesthetic = score_aesthetic(image_tensor)
    result['aesthetic_score'] = aesthetic
    
    # Step 6: Blur
    blur = detect_blur(image_tensor)
    result['blur_score'] = blur
    
    # Step 7: Junk probability
    junk = classify_junk(image_path, image_tensor, result)
    result['junk_probability'] = junk
    
    # Store everything in database
    save_asset_features(asset_id, result)
```

**Batching:** Images are processed in batches of 8-16 to maximize CPU utilization. ONNX Runtime supports parallel inference within each model, and the multiprocessing pool distributes batches across CPU cores.

**Progress contribution:** ~15-50%

---

### Phase 3: Video Intelligence

**Purpose:** Extract meaningful information from videos without processing every frame.

#### Step 3.1 — Keyframe Extraction (FFmpeg)

Videos are not processed frame-by-frame (too slow). Instead, we use **scene-change detection** to extract representative keyframes.

**Method:** FFmpeg's `scene` filter analyzes the video stream and detects moments where the visual content changes significantly. These boundaries represent scene transitions (e.g., switching from a landscape shot to a close-up).

```bash
ffmpeg -i input.mp4 -filter:v "select='gt(scene,0.4)',showinfo" -vsync vfr keyframe_%04d.jpg
```

**Parameters:**
- **Scene threshold:** 0.4 (lower = more sensitive, extracts more keyframes)
- **Maximum keyframes per video:** 50 (limit to avoid explosion on long videos)
- **Minimum interval between keyframes:** 1 second

For videos longer than 20 minutes, the system samples at 1 keyframe per 30 seconds in addition to scene-change detection.

**Thumbnail:** The best representative frame is selected based on:
- Highest aesthetic score (if multiple keyframes)
- Presence of faces (prefer frames with family faces)
- Middle of the video (most representative)

#### Step 3.2 — Process Keyframes

Each extracted keyframe is processed through the **Image Intelligence pipeline** (Phase 2). The per-keyframe results are then **aggregated** for the video:

| Metric | Aggregation Method |
|---|---|
| Max face priority | Maximum across all keyframes |
| Face identities | Union of all detected identities |
| Best aesthetic score | Maximum NIMA score |
| Scene category distribution | Mode (most common scene type) |
| Worst blur score | Minimum Laplacian variance |
| Scene categories | Set of all detected scene types |

**Video-level outputs:**
- **video_score:** Weighted combination of max aesthetic + face presence + scene variety
- **suggested_category:** "Top Family Video" (if high-priority faces), "Travel Clip" (if travel scenes), "Low-value Clip" (if no faces, low quality)
- **best_thumbnail_path:** Path to the representative keyframe

#### Step 3.3 — Video Metadata

In addition to keyframe analysis, the following is extracted via FFprobe:

| Field | Source |
|---|---|
| Duration (seconds) | FFprobe format.duration |
| Codec | FFprobe streams.codec_name |
| Bitrate | FFprobe format.bit_rate |
| Resolution | FFprobe streams.width × height |
| FPS | FFprobe streams.r_frame_rate |
| Audio codec | FFprobe streams (index 1) |
| Creation time | FFprobe format.tags.creation_time |

**Progress contribution:** ~50-65%

---

### Phase 4: Clustering

**Purpose:** Group related content together — burst sequences, trips, events, and face-based similarity.

#### Step 4.1 — FAISS Incremental Index

FAISS (Facebook AI Similarity Search) is a highly optimized library for **similarity search** over dense vectors. PhotoCurator maintains two FAISS indexes on disk:

| Index | Vector type | Dimension | Purpose |
|---|---|---|---|
| `face_index.faiss` | ArcFace embedding | 512 | Face matching, clustering |
| `scene_index.faiss` | CLIP embedding | 512 | Scene similarity, duplicate pruning |

**Key design: Incremental, disk-backed**

Unlike in-memory approaches that require all embeddings to be loaded at once, our FAISS manager:
1. On startup: loads existing index from disk (or creates new)
2. During scan: adds new embeddings one-by-one or in small batches
3. On completion: saves index to disk

This means:
- **No memory limit** — handles 500k+ photos
- **Resumable scans** — partial scan saves progress
- **Incremental updates** — new photos on subsequent scans

```python
class FAISSManager:
    def __init__(self, index_path: str, dimension: int):
        self.index_path = index_path
        self.dimension = dimension
        self.index = self._load_or_create()
    
    def add_embeddings(self, embeddings: np.ndarray, ids: List[int]):
        """Add new embeddings to the index."""
        self.index.add_with_ids(embeddings, ids)
    
    def search(self, query: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Search for k nearest neighbors."""
        return self.index.search(query, k)
    
    def save(self):
        """Persist index to disk."""
        faiss.write_index(self.index, self.index_path)
    
    def _load_or_create(self) -> faiss.Index:
        if os.path.exists(self.index_path):
            return faiss.read_index(self.index_path)
        else:
            return faiss.IndexFlatIP(self.dimension)  # Inner Product = cosine similarity
```

#### Step 4.2 — Burst Clustering

**Definition:** A "burst" is a sequence of near-identical photos taken within a few seconds of each other (common in smartphone burst mode).

**Algorithm:**

```
1. Sort all assets by timestamp ASC
2. Sliding window scan:
   a. If time gap between consecutive photos < 2 seconds → same burst
   b. Within each burst:
      - Compare perceptual hashes (Hamming distance)
      - If all photos have distance < 15 → confirm as genuine burst
   c. If burst confirmed:
      - Pick "hero": highest aesthetic score (NIMA)
      - Pick "backup": second-highest aesthetic score
      - Mark remaining as "pruned" (suggested_action = PRUNE)
      - Store cluster with type = 'burst'
```

**Example:** You take 20 photos of your child blowing out birthday candles:
- Photo 7 (sharp, great expression, high NIMA) → hero
- Photo 12 (second best) → backup
- Photos 1-6, 8-11, 13-20 → pruned

**User-defined hero/backup count** can be adjusted in settings (default: 1 hero + 1 backup).

#### Step 4.3 — Trip Detection

**Purpose:** Automatically identify travel periods in your photo collection.

**Algorithm:** Uses three signals combined:

```
SIGNAL 1: Date Clustering (weight: 0.3)
  ├── Find contiguous date ranges with high photo density
  ├── Minimum trip duration: 2 days
  ├── Maximum trip duration: 14 days
  └── Score: density * duration_coverage

SIGNAL 2: GPS Variance (weight: 0.4)
  ├── If GPS data available:
  ├── Cluster photos by geographic location
  ├── Multiple distinct locations within date window = movement = trip
  ├── Score: number_of_locations / max_possible
  └── If no GPS: neutral score (0.5)

SIGNAL 3: Scene Content (weight: 0.3)
  ├── Analyze scene categories within date window
  ├── High proportion of travel/landscape/outdoor scenes = trip
  ├── Score: travel_scene_count / total_scenes
  └── Includes: landscape, beach, mountain, landmark, hotel, airport, city

FINAL TRIP SCORE = (date_score × 0.3) + (gps_score × 0.4) + (scene_score × 0.3)

If FINAL TRIP SCORE > 0.6 → Mark all assets in window as trip
```

**Naming convention:**
- GPS available → `Trip to {city_name}` (reverse geocoded via a local lookup table)
- No GPS → `Trip — {month} {year}`
- User can rename any trip in the UI

**Trip metadata stored:**
```json
{
  "name": "Trip to Bali",
  "start_date": "2024-06-12",
  "end_date": "2024-06-18",
  "photo_count": 312,
  "locations_visited": ["Airport", "Beach", "Temple", "Hotel"],
  "family_members_present": ["Mom", "Dad", "Sister"],
  "average_quality": 7.8,
  "total_memory_score": 0.82
}
```

#### Step 4.4 — Event Detection

**Purpose:** Find short, intense photo-taking sessions (birthday parties, weddings, family gatherings).

**Algorithm:**

```
1. Find date windows of 1-2 days with high photo density (> 50 photos/day)
2. Within each window:
   a. Count unique faces present
   b. Check face consistency (same set of faces across multiple photos)
   c. Check scene variety (multiple indoor scenes = party, single scene = meeting)
3. If high face density + face consistency → "Event"
4. Score = face_density × consistency × scene_variety
5. If score > 0.7 → create event cluster
```

**Events differ from trips** in:
- Shorter duration (1-2 days vs 2-14 days)
- Higher face density (more people together)
- Less GPS movement (usually single location)

**Progress contribution:** ~65-80%

---

### Phase 5: Scoring & Suggestions

**Purpose:** Assign a MemoryScore to every asset, categorize into suggestion buckets, and calculate confidence levels.

#### Step 5.1 — MemoryScore Formula

Each asset receives a **MemoryScore** between 0.0 (total junk) and 1.0 (priceless memory):

```
MemoryScore = (FacePriority × W1) + (QualityScore × W2) + (SceneScore × W3) - (JunkPenalty × W4)

Where:
  W1 = 0.40 (Face Priority weight)
  W2 = 0.30 (Quality weight)
  W3 = 0.20 (Scene weight)
  W4 = 0.10 (Junk penalty weight)
```

**Component calculations:**

| Component | Formula | Range |
|---|---|---|
| **FacePriority** | `max(face_priority) / 10` | 0.0 - 1.0 |
| **QualityScore** | `(nima_mean - 1) / 9` | 0.0 - 1.0 |
| **SceneScore** | scene_type_weight (see table) | 0.0 - 1.0 |
| **JunkPenalty** | junk_probability (from Phase 2.7) | 0.0 - 1.0 |

**Scene type weights:**

| Scene Type | Weight | Rationale |
|---|---|---|
| Landscape | 0.8 | Beautiful, keepsake-worthy |
| Travel | 0.9 | High memory value |
| Portrait | 0.7 | People photos matter |
| Event | 0.7 | Celebrations |
| Nature | 0.6 | Pleasant but not unique |
| Food | 0.5 | Moderate value |
| Indoor | 0.4 | Everyday life |
| City | 0.6 | Documenting life |
| Art | 0.3 | Low personal memory value |
| Document | 0.1 | Screenshots, receipts |

**Example calculation:**

A photo of Mom at the beach:
- FacePriority: Mom = priority 10 → 10/10 = 1.0
- QualityScore: NIMA = 7.5 → (7.5-1)/9 = 0.72
- SceneScore: "Landscape" → 0.8
- JunkPenalty: Not junk → 0.0

```
MemoryScore = (1.0 × 0.40) + (0.72 × 0.30) + (0.8 × 0.20) - (0.0 × 0.10)
            = 0.40 + 0.216 + 0.16 - 0.0
            = 0.776
```

#### Step 5.2 — Suggestion Category Assignment

Assets are classified into suggestion categories using the following rules:

| Category | Rule | Priority |
|---|---|---|
| **⭐ Top Memories** | `MemoryScore > 0.85` AND `FacePriority > 0` | Highest |
| **👨‍👩‍👧 Family Priority** | `max(face_priority) ≥ 7` (family/extended family) | High |
| **🌍 Travel Highlights** | `is_trip = True` AND `MemoryScore > 0.6` | High |
| **📸 Burst Pruning** | `cluster_role = 'pruned'` | Medium |
| **🗑 Junk** | `junk_probability > 0.7` | Medium |
| **❓ Needs Review** | Everything else | Default |

**An asset can appear in multiple categories.** For example, a high-quality photo of family on a beach vacation might appear in:
- ⭐ Top Memories (MemoryScore > 0.85 AND has faces)
- 👨‍👩‍👧 Family Priority (family faces detected)
- 🌍 Travel Highlights (part of a trip, high quality)

#### Step 5.3 — Confidence Calculation

Every suggestion includes a `confidence_level` to help users trust the AI:

| Level | Threshold | Meaning |
|---|---|---|
| **HIGH** | ≥ 0.90 | Very likely correct. The AI is confident. |
| **MEDIUM** | ≥ 0.70 | Likely correct, but worth reviewing. |
| **LOW** | < 0.70 | Uncertain. User should verify. |

**Confidence is calculated per category:**

- **Junk confidence:** `junk_probability` (already 0-1)
- **Duplicate confidence:** `1 - (hamming_distance / 64)` for perceptual hashes
- **Face match confidence:** `cosine_similarity(embedding, matched_face)`
- **Trip confidence:** `trip_score` (from trip detection algorithm)
- **MemoryScore confidence:** `1 - nima_stddev` (lower NIMA stddev = more reliable score)

**UI display:**
```
🗑 Junk Suggestions (95% confident these 342 images are junk)
```
```
⭐ Top Memories (88% confident)
```

**Progress contribution:** ~80-95%

---

### Phase 6: User Review & Export

**Purpose:** Present all suggestions to the user in a clear, actionable interface, and allow export of decisions.

#### Step 6.1 — Dashboard

The first screen after scanning shows a summary dashboard:

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

#### Step 6.2 — Category Browsing

Each category opens a grid view with image thumbnails:

```
┌─────────────────────────────────────────────────────────┐
│  🗑 Junk Candidates                          Confidence:│
│                                                         │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐        │
│  │ Scre │ │ Blur │ │ WApp │ │ Dup  │ │ Low  │  HIGH   │
│  │ enshot│ │ ry   │ │      │ │      │ │ Qual │         │
│  │      │ │      │ │      │ │      │ │      │         │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘        │
│  [Keep] [Del] [Keep] [Del] [Keep] [Del] [Keep] [Del]  │
│                                                         │
│  File: C:\Photos\WhatsApp\IMG-20240301-WA0001.jpg      │
│  Reason: WhatsApp forward (93% confident)              │
│  Resolution: 720×1280                                  │
│  Face count: 0                                         │
│  Aesthetic score: 2.1/10                               │
└─────────────────────────────────────────────────────────┘
```

Each card shows:
- Thumbnail preview
- Reason for suggestion
- Confidence level (colored badge)
- Action buttons: Keep / Delete Candidate / Review

#### Step 6.3 — Face Labeling

After the first scan, the user is prompted to label face clusters:

```
┌─────────────────────────────────────────────────────────┐
│  Who's in your photos?                                  │
│                                                         │
│  We found 47 unique people. Help us identify them:      │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Face 1   │ │ Face 2   │ │ Face 3   │ │ Face 4   │  │
│  │ (2,341)  │ │ (1,892)  │ │ (1,234)  │ │ (892)    │  │
│  │ Name:____ │ │ Name:____ │ │ Name:____ │ │ Name:____ │  │
│  │ Priority▼ │ │ Priority▼ │ │ Priority▼ │ │ Priority▼ │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐                │
│  │ Unknown  │ │ Unknown  │ │ Unknown  │  ...            │
│  │ (12)     │ │ (8)       │ │ (5)       │                │
│  │ Low pri  │ │ Low pri   │ │ Low pri   │                │
│  └──────────┘ └──────────┘ └──────────┘                │
│                                                         │
│  [Skip labeling for now]                                │
└─────────────────────────────────────────────────────────┘
```

Clusters with fewer than ~10 photos are automatically marked as Unknown until the user labels them.

#### Step 6.4 — Export

Users can export their decisions as CSV or JSON:

**CSV format:**
```csv
file_path,type,category,suggested_action,confidence,reason
C:\Photos\IMG_0001.jpg,image,Top Memories,KEEP,0.92,Family photo: Mom (priority 10)
C:\Photos\IMG_0002.jpg,image,Junk,DELETE_CANDIDATE,0.95,Screenshot
C:\Photos\IMG_0003.jpg,image,Burst Pruning,PRUNE,0.88,Duplicate of IMG_0001
Videos\vacation.mp4,video,Travel Highlights,KEEP,0.85,Trip to Bali
```

**JSON format:**
```json
{
  "export_date": "2024-06-15T10:30:00",
  "source_folder": "C:\\Photos",
  "total_assets": 34892,
  "assets": [
    {
      "file_path": "C:\\Photos\\IMG_0001.jpg",
      "type": "image",
      "category": "Top Memories",
      "suggested_action": "KEEP",
      "confidence": 0.92,
      "reason": "Family photo: Mom (priority 10)",
      "memory_score": 0.88,
      "faces": ["Mom"]
    }
  ]
}
```

**Progress contribution:** ~95-100%

---

## Suggestion Categories

### Complete Reference

| # | Category | Icon | Default Action | Criteria | Priority |
|---|---|---|---|---|---|
| 1 | **Top Memories** | ⭐ | KEEP | MemoryScore > 0.85 AND faces detected | Highest |
| 2 | **Family Priority** | 👨‍👩‍👧 | KEEP | Any face with priority ≥ 7 | High |
| 3 | **Travel Highlights** | 🌍 | KEEP | is_trip AND MemoryScore > 0.6 | High |
| 4 | **Burst Pruning** | 📸 | PRUNE | Cluster role = 'pruned' | Medium |
| 5 | **Junk Candidates** | 🗑 | DELETE_CANDIDATE | junk_probability > 0.7 | Medium |
| 6 | **Needs Review** | ❓ | REVIEW | Everything else | Default |

### What Happens to Each

| Action | Meaning | Phase 1 Behavior |
|---|---|---|
| **KEEP** | This is a valuable memory | Nothing — it stays as-is |
| **PRUNE** | Too many similar photos | Marked for user review |
| **DELETE_CANDIDATE** | This is likely junk | Marked for user to delete manually |
| **ARCHIVE** | Low value, keep for reference | Marked for user to move to archive |
| **REVIEW** | Uncertain, needs human judgment | User must decide |

> **Important:** In Phase 1, NO action is taken on files. Everything is a suggestion stored as metadata. The user reviews and decides.

---

## Face Recognition System

### Detailed Flow

```
First Scan:
    │
    ▼
Detect all faces across all photos
    │
    ▼
Run FAISS clustering on all face embeddings
(DBSCAN with eps=0.6, min_samples=3)
    │
    ▼
Generate face clusters:
  Cluster A: 2,341 photos (Mom)
  Cluster B: 1,892 photos (Dad)
  Cluster C: 1,234 photos (Sister)
  Cluster D:   34 photos (Unknown #1)
  Cluster E:   12 photos (Unknown #2)
  ...
    │
    ▼
Show face clusters to user for labeling
    │
    ▼
User labels known faces:
  - Cluster A → "Mom", priority 10
  - Cluster B → "Dad", priority 10
  - Cluster C → "Sister", priority 7
  - Cluster D → "Neighbor", priority 5
  - Clusters E-Z → Stay "Unknown", priority 1
    │
    ▼
Store labeled identities in `faces` table
FAISS index now contains all known embeddings

Subsequent Scans:
    │
    ▼
For each new face embedding:
    │
    ▼
FAISS search (k=1) against known face index
    │
    ├── Cosine similarity > 0.85 → Auto-match, assign identity
    ├── Cosine similarity 0.7 - 0.85 → Flag for user review
    └── Cosine similarity < 0.7 → Save as new unknown
```

### Similarity Thresholds

| Threshold | Action |
|---|---|
| > 0.90 | Very confident match, auto-assign |
| 0.85 - 0.90 | Confident match, auto-assign |
| 0.70 - 0.85 | Possible match, ask user |
| 0.50 - 0.70 | Weak match, treat as unknown |
| < 0.50 | Different person |

### Face Merge

Over time, the same person might be stored under multiple unknown IDs. Periodically, FAISS re-clusters all unknown embeddings. If two unknown clusters overlap significantly (centroid distance < 0.4), they are merged into a single identity and the user is prompted to label the merged cluster.

---

## Trip & Event Detection

### Trip Detection Algorithm (Detailed)

```python
def detect_trips(assets):
    """Find all trips in the asset collection."""
    
    # Step 1: Sort by timestamp
    sorted_assets = sorted(assets, key=lambda a: a.timestamp)
    
    # Step 2: Find date clusters
    trips = []
    current_cluster = []
    
    for asset in sorted_assets:
        if not current_cluster:
            current_cluster.append(asset)
            continue
        
        gap = (asset.timestamp - current_cluster[-1].timestamp).days
        if gap <= 1:
            # Continuation of current cluster (allow 1-day gap)
            current_cluster.append(asset)
        else:
            # Gap too large, evaluate current cluster
            if len(current_cluster) >= 10:  # Minimum 10 photos for a trip
                trip_score = evaluate_trip(current_cluster)
                if trip_score > 0.6:
                    trips.append(build_trip(current_cluster, trip_score))
            current_cluster = [asset]
    
    # Step 3: Score each cluster
    def evaluate_trip(cluster):
        date_range = (cluster[-1].timestamp - cluster[0].timestamp).days
        
        # Signal 1: Date density (2-14 days = trip-like)
        if 2 <= date_range <= 14:
            date_score = 1.0 - (abs(date_range - 7) / 7)  # Peak at 7 days
        else:
            date_score = 0.0
        
        # Signal 2: GPS variance
        gps_locations = set((a.gps_lat, a.gps_lon) for a in cluster if a.gps_lat)
        if len(gps_locations) >= 2:
            gps_score = min(len(gps_locations) / 5, 1.0)
        else:
            gps_score = 0.3  # Neutral with penalty
        
        # Signal 3: Scene content
        travel_scenes = {'landscape', 'beach', 'mountain', 'landmark', 
                        'city', 'airport', 'hotel', 'sunset'}
        scene_matches = sum(
            1 for a in cluster if a.scene_category in travel_scenes
        )
        scene_score = scene_matches / len(cluster) if cluster else 0
        
        # Weighted combination
        return (date_score * 0.3) + (gps_score * 0.4) + (scene_score * 0.3)
    
    return trips
```

### Event Detection Algorithm (Detailed)

```python
def detect_events(assets, face_engine):
    """Find short-duration events like parties, weddings."""
    
    # Step 1: Group by date
    by_date = defaultdict(list)
    for asset in assets:
        by_date[asset.timestamp.date()].append(asset)
    
    events = []
    
    # Step 2: Check each single-date group
    for date, day_assets in by_date.items():
        if len(day_assets) < 20:  # Minimum 20 photos for an event
            continue
        
        # Collect face identities across all photos
        face_set = set()
        for asset in day_assets:
            faces = face_engine.get_faces_for_asset(asset.id)
            face_set.update(f[0] for f in faces)  # face IDs
        
        # Signal 1: Face diversity
        face_density = len(face_set) / len(day_assets)
        
        # Signal 2: Face consistency (same people across photos)
        face_frequencies = Counter()
        for asset in day_assets:
            faces = face_engine.get_faces_for_asset(asset.id)
            for face_id, _ in faces:
                face_frequencies[face_id] += 1
        consistent_faces = sum(1 for f, c in face_frequencies.items() 
                              if c > len(day_assets) * 0.3)
        consistency_score = consistent_faces / max(len(face_set), 1)
        
        # Signal 3: Time span within day
        timestamps = [a.timestamp for a in day_assets]
        time_span = (max(timestamps) - min(timestamps)).seconds / 3600  # hours
        time_score = min(time_span / 6, 1.0) if time_span > 1 else 0.3
        
        event_score = (face_density + consistency_score + time_score) / 3
        
        if event_score > 0.6:
            events.append({
                'date': date,
                'asset_count': len(day_assets),
                'unique_faces': len(face_set),
                'score': event_score,
                'assets': [a.id for a in day_assets],
            })
    
    return events
```

---

## Database Schema

### SQLite Tables

#### `assets`

The core table — one row per photo or video.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `path` | TEXT NOT NULL | Absolute file path |
| `sha256` | TEXT | SHA-256 hash (unique) |
| `phash` | TEXT | Perceptual hash (64-bit hex) |
| `file_type` | TEXT | 'image' or 'video' |
| `mime_type` | TEXT | e.g., 'image/jpeg' |
| `timestamp` | DATETIME | From EXIF or file mtime |
| `gps_lat` | REAL | GPS latitude |
| `gps_lon` | REAL | GPS longitude |
| `resolution` | TEXT | e.g., '4032×3024' |
| `file_size` | INTEGER | Bytes |
| `duration` | REAL | Video duration (seconds, NULL for images) |
| `orientation` | INTEGER | EXIF orientation (1-8) |
| `camera_make` | TEXT | Camera manufacturer |
| `camera_model` | TEXT | Camera model |
| `scene_category` | TEXT | e.g., 'landscape', 'portrait' |
| `aesthetic_score` | REAL | NIMA score (1-10) |
| `blur_score` | REAL | Laplacian variance |
| `junk_probability` | REAL | 0.0 - 1.0 |
| `memory_score` | REAL | 0.0 - 1.0 |
| `confidence` | REAL | 0.0 - 1.0 |
| `suggested_action` | TEXT | KEEP, PRUNE, DELETE_CANDIDATE, ARCHIVE, REVIEW |
| `is_trip` | INTEGER | Boolean (0 or 1) |
| `trip_id` | TEXT | FK to clusters table |
| `status` | TEXT | pending, processing, done, error |
| `error_msg` | TEXT | Error details if failed |
| `face_count` | INTEGER | Number of detected faces |
| `created_at` | DATETIME | When record was created |
| `updated_at` | DATETIME | When record was last updated |

**Indexes:**
- `idx_assets_path` on `path`
- `idx_assets_sha256` on `sha256` (unique)
- `idx_assets_timestamp` on `timestamp`
- `idx_assets_suggested_action` on `suggested_action`
- `idx_assets_status` on `status`
- `idx_assets_trip_id` on `trip_id`

#### `faces`

One row per unique person detected across all photos.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `label` | TEXT | User-given name (NULL if unknown) |
| `priority` | INTEGER | 1-10 (default 1) |
| `embedding` | BLOB | 512-dim Float32 embedding |
| `sample_image_path` | TEXT | Path to representative thumbnail |
| `is_known` | INTEGER | Boolean (user has labeled this face) |
| `total_photos` | INTEGER | Number of photos this face appears in |
| `metadata` | TEXT (JSON) | Additional info |
| `created_at` | DATETIME | |

#### `asset_faces`

Many-to-many relationship between assets and faces.

| Column | Type | Description |
|---|---|---|
| `asset_id` | TEXT (UUID) | FK to assets.id |
| `face_id` | TEXT (UUID) | FK to faces.id |
| `confidence` | REAL | Matching confidence (0-1) |

**Indexes:**
- `idx_asset_faces_asset` on `asset_id`
- `idx_asset_faces_face` on `face_id`

#### `clusters`

Groups of related assets (bursts, trips, events).

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `type` | TEXT | 'burst', 'trip', 'event' |
| `name` | TEXT | Auto-generated or user-given name |
| `hero_asset_id` | TEXT (UUID) | FK to best representative asset |
| `backup_asset_id` | TEXT (UUID) | FK to second-best |
| `metadata` | TEXT (JSON) | Type-specific details |
| `score` | REAL | Cluster quality/confidence score |
| `created_at` | DATETIME | |

#### `cluster_assets`

Assets within a cluster.

| Column | Type | Description |
|---|---|---|
| `cluster_id` | TEXT (UUID) | FK to clusters.id |
| `asset_id` | TEXT (UUID) | FK to assets.id |
| `role` | TEXT | 'hero', 'backup', 'pruned', 'member' |

#### `processing_status`

Tracks scan jobs and their progress.

| Column | Type | Description |
|---|---|---|
| `id` | TEXT (UUID) | Primary key |
| `source_folder` | TEXT | The scanned folder path |
| `status` | TEXT | running, completed, failed, cancelled |
| `total_assets` | INTEGER | Total found |
| `processed_assets` | INTEGER | Completed so far |
| `current_phase` | TEXT | ingestion, intelligence, clustering, scoring |
| `current_file` | TEXT | Currently processing file |
| `started_at` | DATETIME | |
| `completed_at` | DATETIME | |

#### `settings`

Persistent user preferences.

| Column | Type | Description |
|---|---|---|
| `key` | TEXT | Setting name |
| `value` | TEXT | Setting value (JSON-encoded) |

**Default settings:**
```json
{
  "weights": {
    "face_priority": 0.4,
    "quality": 0.3,
    "scene": 0.2,
    "junk_penalty": 0.1
  },
  "burst": {
    "hero_count": 1,
    "backup_count": 1,
    "time_window_seconds": 2,
    "phash_threshold": 15
  },
  "face": {
    "auto_match_threshold": 0.85,
    "review_threshold": 0.70,
    "cluster_eps": 0.6,
    "min_cluster_size": 3
  },
  "trip": {
    "min_days": 2,
    "max_days": 14,
    "min_photos": 10,
    "score_threshold": 0.6
  },
  "junk": {
    "min_resolution": 200,
    "blur_threshold": 20,
    "probability_threshold": 0.7
  },
  "confidence": {
    "high_threshold": 0.9,
    "medium_threshold": 0.7
  }
}
```

---

## API Reference

### Base URL

```
http://localhost:8765/api/v1
```

### Endpoints

#### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "models_loaded": ["retinaface", "arcface", "clip", "nima"],
  "database_size_mb": 45.2,
  "total_assets": 34892,
  "python_version": "3.11.0"
}
```

---

#### Start Scan

```
POST /scan
```

**Request:**
```json
{
  "path": "C:/Users/Me/Pictures"
}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "estimated_assets": null
}
```

---

#### Scan Progress

```
GET /scan/{job_id}
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "phase": "intelligence",
  "progress_percent": 42.5,
  "total_assets": 34892,
  "processed_assets": 14823,
  "current_file": "C:/Photos/IMG_8421.jpg",
  "elapsed_seconds": 1847,
  "estimated_remaining_seconds": 2493
}
```

---

#### List Faces

```
GET /faces
```

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `known_only` | boolean | false | Only show labeled faces |
| `min_count` | integer | 1 | Minimum photos for this face |
| `page` | integer | 1 | Page number |
| `per_page` | integer | 50 | Items per page |

**Response:**
```json
{
  "faces": [
    {
      "id": "face-001",
      "label": "Mom",
      "priority": 10,
      "is_known": true,
      "photo_count": 2341,
      "sample_thumbnail": "/thumbnails/face-001.jpg"
    },
    {
      "id": "face-002",
      "label": null,
      "priority": 1,
      "is_known": false,
      "photo_count": 34,
      "sample_thumbnail": "/thumbnails/face-002.jpg"
    }
  ],
  "total": 47,
  "page": 1,
  "per_page": 50
}
```

---

#### Label a Face

```
PUT /faces/{face_id}
```

**Request:**
```json
{
  "label": "Mom",
  "priority": 10
}
```

**Response:**
```json
{
  "id": "face-001",
  "label": "Mom",
  "priority": 10,
  "status": "updated"
}
```

---

#### Get Suggestions

```
GET /suggestions
```

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `category` | string | null | Filter: keep, family, travel, burst, junk, review |
| `confidence` | string | null | Filter: high, medium, low |
| `action` | string | null | Filter: keep, prune, delete_candidate, archive, review |
| `type` | string | null | Filter: image, video |
| `trip_id` | string | null | Filter by specific trip |
| `face_id` | string | null | Filter by specific face |
| `page` | integer | 1 | Page number |
| `per_page` | integer | 50 | Items per page |
| `sort_by` | string | memory_score | memory_score, timestamp, confidence |
| `sort_order` | string | desc | asc, desc |

**Response:**
```json
{
  "suggestions": [
    {
      "asset_id": "asset-001",
      "path": "C:/Photos/IMG_0001.jpg",
      "type": "image",
      "thumbnail": "/thumbnails/asset-001.jpg",
      "categories": ["top_memories", "family_priority"],
      "suggested_action": "KEEP",
      "reason": "Family photo: Mom (priority 10)",
      "confidence": "HIGH",
      "confidence_score": 0.95,
      "memory_score": 0.88,
      "timestamp": "2024-06-12T14:30:00",
      "face_count": 2,
      "faces": ["Mom", "Dad"]
    }
  ],
  "total": 143,
  "page": 1,
  "per_page": 50,
  "filters": {
    "category": "top_memories",
    "confidence": null,
    "action": null
  }
}
```

---

#### Get Summary

```
GET /summary
```

**Response:**
```json
{
  "source_folder": "C:/Photos",
  "total_assets": 34892,
  "total_images": 34658,
  "total_videos": 234,
  "total_size_mb": 142342,
  "by_category": {
    "top_memories": { "count": 143, "percent": 0.4, "estimated_size_mb": 284 },
    "family_priority": { "count": 2341, "percent": 6.7, "estimated_size_mb": 4682 },
    "travel_highlights": { "count": 4212, "percent": 12.1, "estimated_size_mb": 8424 },
    "burst_pruning": { "count": 1876, "percent": 5.4, "estimated_size_mb": 3752 },
    "junk": { "count": 8943, "percent": 25.6, "estimated_size_mb": 17886 },
    "needs_review": { "count": 17377, "percent": 49.8, "estimated_size_mb": 107314 }
  },
  "by_action": {
    "KEEP": { "count": 6696, "percent": 19.2 },
    "PRUNE": { "count": 1876, "percent": 5.4 },
    "DELETE_CANDIDATE": { "count": 8943, "percent": 25.6 },
    "REVIEW": { "count": 17377, "percent": 49.8 }
  },
  "reclaimable_space_mb": 21638,
  "trips": 12,
  "faces": {
    "total": 47,
    "known": 8,
    "unknown": 39
  },
  "face_stats": {
    "most_common": { "label": "Mom", "count": 2341 },
    "photos_with_faces": 8921,
    "percent_with_faces": 25.6
  },
  "processing_time_seconds": 4320
}
```

---

#### Get Trips

```
GET /trips
```

**Response:**
```json
{
  "trips": [
    {
      "id": "trip-001",
      "name": "Trip to Bali",
      "start_date": "2024-06-12",
      "end_date": "2024-06-18",
      "photo_count": 312,
      "video_count": 5,
      "memory_score_avg": 0.82,
      "total_size_mb": 624,
      "faces_present": ["Mom", "Dad", "Sister"],
      "locations": ["Airport", "Beach", "Temple"]
    }
  ]
}
```

---

#### Export Report

```
GET /export
```

**Query Parameters:**
| Param | Type | Default | Description |
|---|---|---|---|
| `format` | string | csv | csv or json |
| `category` | string | null | Filter by category |
| `action` | string | null | Filter by suggested action |
| `include_reviewed` | boolean | false | Include previously reviewed items |

**Response:** File download (Content-Type: text/csv or application/json)

---

#### Record Feedback

```
PUT /feedback
```

**Request:**
```json
{
  "asset_id": "asset-001",
  "user_action": "keep",
  "previous_suggestion": "DELETE_CANDIDATE"
}
```

**Response:**
```json
{
  "status": "recorded"
}
```

This feedback data is stored locally for future adaptive learning (Phase 2 feature).

---

#### Get Settings

```
GET /settings
```

**Response:**
```json
{
  "weights": {
    "face_priority": 0.4,
    "quality": 0.3,
    "scene": 0.2,
    "junk_penalty": 0.1
  },
  "burst": {
    "hero_count": 1,
    "backup_count": 1
  },
  "confidence": {
    "high_threshold": 0.9,
    "medium_threshold": 0.7
  }
}
```

---

#### Update Settings

```
PUT /settings
```

**Request:**
```json
{
  "weights": {
    "face_priority": 0.5,
    "quality": 0.25,
    "scene": 0.15,
    "junk_penalty": 0.1
  }
}
```

**Response:**
```json
{
  "status": "updated",
  "note": "MemoryScore will be recalculated on next scan"
}
```

---

## Project Structure

```
photocurator/
│
├── package.json                    # Root package.json (Electron + React)
├── electron-builder.yml            # Packing config for installers
├── tsconfig.json                   # TypeScript config
├── vite.config.ts                  # Vite config (React bundler)
├── tailwind.config.js              # Tailwind CSS config
│
├── electron/                       # ── Electron shell
│   ├── main.ts                     # Main process: window, Python lifecycle
│   ├── preload.ts                  # Context bridge for IPC
│   └── python-manager.ts           # Spawn / monitor / kill Python backend
│
├── frontend/                       # ── React UI
│   ├── index.html                  # HTML entry point
│   ├── vite.config.ts              # Vite config for bundling
│   ├── tailwind.config.js          # CSS utility framework
│   ├── src/
│   │   ├── main.tsx                # React entry point
│   │   ├── App.tsx                 # Root component with routing
│   │   │
│   │   ├── api/                    # API client layer
│   │   │   ├── client.ts           # Axios instance (base URL: localhost:8765)
│   │   │   ├── scan.ts             # POST /scan, GET /scan/{id}
│   │   │   ├── suggestions.ts      # GET /suggestions
│   │   │   ├── faces.ts            # GET /faces, PUT /faces/{id}
│   │   │   ├── summary.ts          # GET /summary
│   │   │   ├── trips.ts            # GET /trips
│   │   │   ├── export.ts           # GET /export
│   │   │   ├── settings.ts         # GET/PUT /settings
│   │   │   └── feedback.ts         # PUT /feedback
│   │   │
│   │   ├── pages/                  # Route pages
│   │   │   ├── Welcome.tsx         # Folder picker, start scan
│   │   │   ├── ScanProgress.tsx    # Progress bar, logs, ETA
│   │   │   ├── Dashboard.tsx       # Summary stats, navigation cards
│   │   │   ├── FaceLabeling.tsx    # "Who's who?" face grid
│   │   │   ├── Suggestions.tsx     # Category tabs, image grid
│   │   │   ├── TripView.tsx        # Trip overview page
│   │   │   ├── ExportPage.tsx      # Export options
│   │   │   └── Settings.tsx        # Weights, thresholds, preferences
│   │   │
│   │   ├── components/             # Reusable UI components
│   │   │   ├── Layout.tsx          # App shell: sidebar + content
│   │   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   │   ├── CategoryTabs.tsx    # Tab bar for categories
│   │   │   ├── SuggestionCard.tsx  # Single suggestion with thumbnail
│   │   │   ├── ImagePreview.tsx    # Modal preview with details
│   │   │   ├── ProgressBar.tsx     # Animated progress bar
│   │   │   ├── FaceCircle.tsx      # Face thumbnail circle
│   │   │   ├── StatCard.tsx        # Summary stat display card
│   │   │   ├── ConfidenceBadge.tsx # Color-coded confidence indicator
│   │   │   └── EmptyState.tsx      # Empty state placeholder
│   │   │
│   │   └── types/                  # TypeScript type definitions
│   │       └── index.ts
│   │
│   └── public/                     # Static assets
│
├── backend/                        # ── Python backend (FastAPI)
│   ├── requirements.txt            # Python dependencies
│   ├── pyproject.toml              # Python project metadata
│   ├── main.py                     # FastAPI app entry point
│   ├── config.py                   # Configuration via pydantic-settings
│   ├── database.py                 # SQLite connection, session, init
│   ├── models.py                   # SQLAlchemy ORM models
│   ├── schemas.py                  # Pydantic request/response models
│   │
│   ├── routers/                    # API route handlers
│   │   ├── __init__.py
│   │   ├── health.py               # GET /health
│   │   ├── scan.py                 # POST /scan, GET /scan/{id}
│   │   ├── faces.py                # GET /faces, PUT /faces/{id}
│   │   ├── suggestions.py          # GET /suggestions
│   │   ├── summary.py              # GET /summary
│   │   ├── trips.py                # GET /trips
│   │   ├── export.py               # GET /export
│   │   ├── feedback.py             # PUT /feedback
│   │   └── settings.py             # GET/PUT /settings
│   │
│   ├── ingestion/                  # ── Phase 1: Ingestion
│   │   ├── __init__.py
│   │   ├── scanner.py              # Recursive file walker
│   │   ├── hasher.py               # SHA-256 + perceptual hash
│   │   └── metadata.py             # EXIF + FFprobe extraction
│   │
│   ├── intelligence/               # ── Phase 2: Image AI
│   │   ├── __init__.py
│   │   ├── preprocessor.py         # Resize, normalize, CHW
│   │   ├── face_detector.py        # RetinaFace ONNX
│   │   ├── face_encoder.py         # ArcFace ONNX
│   │   ├── scene_encoder.py        # CLIP ONNX
│   │   ├── aesthetic_scorer.py     # NIMA ONNX
│   │   ├── blur_detector.py        # Laplacian variance
│   │   ├── junk_detector.py        # Heuristics + OCR
│   │   └── pipeline.py             # Orchestrator
│   │
│   ├── video/                      # ── Phase 3: Video
│   │   ├── __init__.py
│   │   ├── keyframer.py            # FFmpeg scene detection
│   │   └── scorer.py               # Aggregate video scores
│   │
│   ├── clustering/                 # ── Phase 4: Clustering
│   │   ├── __init__.py
│   │   ├── faiss_manager.py        # Incremental FAISS index
│   │   ├── burst.py                # Burst sequence grouping
│   │   ├── trip_detector.py        # Trip detection algorithm
│   │   └── event_detector.py       # Event detection
│   │
│   ├── scoring/                    # ── Phase 5: Scoring
│   │   ├── __init__.py
│   │   ├── memory_score.py         # MemoryScore formula
│   │   ├── suggestion_engine.py    # Category assignment
│   │   └── confidence.py           # Confidence calculation
│   │
│   ├── models/                     # ── AI model management
│   │   ├── __init__.py
│   │   ├── onnx_loader.py          # Lazy-load ONNX sessions
│   │   └── downloader.py           # Download from HuggingFace
│   │
│   ├── worker.py                   # Background task runner (threads)
│   └── utils/                      # Utility functions
│       ├── __init__.py
│       ├── file_utils.py           # Path, extension utilities
│       └── logging.py              # Structured logging
│
├── scripts/                        # Development scripts
│   ├── dev.sh                      # Start backend + frontend for dev
│   ├── build-python.sh             # PyInstaller bundle
│   └── build-all.sh                # Full production build
│
└── tests/                          # Test suite
    ├── conftest.py                 # Pytest fixtures
    ├── test_ingestion.py           # Scanner, hasher, metadata tests
    ├── test_intelligence.py        # Face, scene, aesthetic tests
    ├── test_clustering.py          # Burst, trip, event tests
    ├── test_scoring.py             # MemoryScore, suggestion tests
    └── test_api.py                 # API endpoint integration tests
```

---

## Packaging & Distribution

### Building the Installer

PhotoCurator uses **electron-builder** for packaging. The Python backend is compiled to a standalone executable via **PyInstaller**.

#### Installer Contents

```
PhotoCurator-Setup-1.0.0.exe  (~50-60 MB)
│
├── Electron runtime (Chromium + Node.js)
├── React frontend (compiled HTML/JS/CSS)
├── Python backend (PyInstaller-compiled .exe)
├── FFmpeg 7.0 binary
└── Data directories created on first launch:
    ├── ~/.photocurator/db/          # SQLite database
    ├── ~/.photocurator/faiss/       # FAISS indexes
    ├── ~/.photocurator/models/      # ONNX model files (~300MB)
    ├── ~/.photocurator/thumbnails/  # Generated previews
    └── ~/.photocurator/logs/        # Application logs
```

#### First Launch

On first launch, the app:
1. Creates the data directory structure
2. Downloads ONNX models from HuggingFace (with progress UI)
3. Initializes SQLite database schema
4. Shows the Welcome screen

#### Model Download

| Model | Size | Source | Purpose |
|---|---|---|---|
| RetinaFace | ~5 MB | ONNX Model Zoo | Face detection |
| ArcFace | ~12 MB | ONNX Model Zoo | Face embedding |
| CLIP ViT-B/32 | ~170 MB | HuggingFace (ONNX export) | Scene understanding |
| NIMA | ~8 MB | Custom ONNX export | Aesthetic scoring |

**Total:** ~195 MB (compressed), ~300 MB (uncompressed on disk)

The download progress is shown in the UI with a progress bar. A stable internet connection is required only during first launch.

---

## Safety & Privacy

### Phase 1 Rules (Strictly Enforced)

| Rule | Rationale |
|---|---|
| ❌ Never modify original files | Users fear losing memories |
| ❌ Never rename files | Preserves folder organization |
| ❌ Never move files | Preserves folder structure |
| ❌ Never change timestamps | Preserves original metadata |
| ✅ Store file hashes | Verifies file integrity |
| ✅ Store original paths | Provides traceability |
| ✅ All processing local | No data leaves the machine |

### Data Storage

- **All data** is stored locally in `~/.photocurator/`
- **No cloud services** are contacted (except model download on first launch)
- **No analytics, no telemetry, no user tracking**
- **No network requests** after initial model download

### Trust Factors

The UI is designed to build trust:

- **Confidence levels** on every suggestion (HIGH/MEDIUM/LOW)
- **Reasons** explaining why each suggestion was made
- **Thumbnail previews** so users can verify before deciding
- **No auto-delete** — user must explicitly choose to delete files themselves
- **Export report** as a record of all suggestions and decisions

---

## Build & Development

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Node.js | ≥ 18 | For Electron + React |
| Python | ≥ 3.10 | For backend |
| Poetry or pip | Latest | Python package management |
| FFmpeg | ≥ 6.0 | For video processing (system install or bundled) |

### Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourname/photocurator.git
cd photocurator

# 2. Install Python dependencies
cd backend
pip install -r requirements.txt
# or: poetry install
cd ..

# 3. Install Node.js dependencies
npm install

# 4. Start development servers
npm run dev
# This runs:
#   - Python backend on localhost:8765
#   - Vite dev server on localhost:5173
#   - Electron window pointing to Vite dev server
```

### Development Workflow

```bash
# Run only the Python backend (for API testing)
npm run dev:backend

# Run only the React frontend (for UI development)
npm run dev:frontend

# Run tests
npm run test:backend     # Pytest
npm run test:frontend    # Vitest

# Build for production
npm run build            # Builds React, bundles Python, packages Electron
```

### Production Build

```bash
# Build for current platform
npm run build

# Build for specific platforms
npm run build:win        # Windows .exe
npm run build:mac        # macOS .dmg
npm run build:linux      # Linux .AppImage
```

---

## FAQ

### Does the app work offline?
Yes. After the initial model download (first launch), everything runs entirely offline. No internet connection is required.

### How long does a scan take?
For a library of 50,000 images on a modern CPU (8 cores):
- Ingestion: ~2-5 minutes
- AI processing: ~2-4 hours (the bulk of the time)
- Clustering + Scoring: ~10-30 minutes
- **Total: ~3-5 hours**

The scan is resumable — if you close the app, it picks up where it left off.

### Will the app delete my files?
**No.** Phase 1 is suggestion-only. The app never deletes, moves, renames, or modifies any file. It only stores metadata and suggestions in its database. You review suggestions and decide what to do with your files manually.

### Is my data sent to the cloud?
**No.** Everything runs locally on your computer. No data leaves your machine. The only external request is the initial ONNX model download from HuggingFace.

### Can I use it on an external hard drive?
Yes. Select any folder — internal drive, external USB drive, NAS mount point. The app reads files directly from wherever they are.

### Does it work with both photos and videos?
Yes. Supports JPG, PNG, HEIC, WebP for images and MP4, MOV, AVI, MKV for videos.

### Can I run it on a laptop with no GPU?
Yes. The app is designed for CPU-only inference. All models use ONNX Runtime with CPU optimizations (quantization, integer operations). A laptop CPU from the last 3-4 years is sufficient.

### What if I have more than 100,000 photos?
The system is designed to scale. SQLite handles millions of rows, FAISS indexes are disk-backed (not memory-bound), and the processing pipeline is batch-based. 500k+ photos is feasible, though processing will take proportionally longer.

### Can I adjust the scoring weights?
Yes. The Settings page allows you to adjust MemoryScore component weights (face priority, quality, scene, junk penalty). Changes take effect on the next scan.

### What if I relabel a face?
All suggestions are recalculated based on the new face priority. You don't need to re-scan — the system re-scores existing embeddings with the updated priority values.

### Can I export my decisions?
Yes. Export to CSV or JSON with full file paths, reasons, confidence scores, and your decisions.
