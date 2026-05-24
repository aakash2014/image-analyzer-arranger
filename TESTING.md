# PhotoCurator MVP — Test Cases

## Prerequisites

- Python 3.10+ installed
- Dependencies installed: `pip install -r requirements.txt`
- Server running: `python backend/main.py` (listens on `http://localhost:8765`)
- Use a **second terminal** to run the test commands

---

## Test Case 1: Server Health

**Purpose:** Verify the API server is running.

```powershell
curl http://localhost:8765/health
```

**Expected output:**
```json
{"status": "ok", "version": "0.1.0"}
```

**If it fails:**
- Server not started → run `python backend/main.py`
- Port conflict → kill other process on port 8765
- Module not found → run from project root with `PYTHONPATH`

---

## Test Case 2: Scan a Folder of Mixed Photos

**Purpose:** Verify the pipeline processes images end-to-end.

**Setup:** Create `C:\test-photos\` with 10-20 random photos (mix of portraits, landscapes, screenshots).

```powershell
curl -X POST http://localhost:8765/scan ^
  -H "Content-Type: application/json" ^
  -d '{"folder": "C:\\test-photos"}'
```

**Expected output:**
```json
{"scan_job_id": 1, "message": "Scan started"}
```

**Poll until complete:**
```powershell
curl http://localhost:8765/scan/1
```

**Expected final status:** `"status": "completed"`

**If it fails:**
- Check `error_message` in the scan status
- Ensure the folder path exists and has read permission
- Check server console for Python traceback

---

## Test Case 3: Check Summary Dashboard

**Purpose:** Verify statistics are computed correctly.

```powershell
curl http://localhost:8765/summary | python -m json.tool
```

**Expected output shape:**
```json
{
  "total_assets": 15,
  "analyzed_assets": 15,
  "total_faces_detected": 5,
  "face_clusters": 0,
  "suggestions": {
    "top_memories": 0,
    "family_priority": 0,
    "burst_pruning": 0,
    "junk": 2,
    "needs_review": 13
  }
}
```

**Check:**
- `total_assets` matches file count in the folder
- `analyzed_assets` should equal `total_assets`
- `total_faces_detected` > 0 if any photos contain faces
- Category counts sum to total (approximately)

**Failure modes:**
- `analyzed_assets` < `total_assets` → some images failed AI pipeline (check logs)
- Zero faces detected but folder has faces → face detection model may not have loaded

---

## Test Case 4: View All Suggestions

**Purpose:** Inspect per-file suggestion details.

```powershell
curl http://localhost:8765/suggestions | python -m json.tool
```

**Expected output:** A JSON object with categories as keys. Each key contains a list of suggestions.

Example structure:
```json
{
  "junk": [ { "file_path": "...", "reason": "...", "confidence": 0.76 } ],
  "needs_review": [ { "file_path": "...", "reason": "...", "confidence": 0.83 } ]
}
```

**Check per entry:**
- `file_path` — full path to the image (verify it exists)
- `confidence` — between 0 and 1
- `reason` — explains why this category was assigned
- `memory_score` — between 0 and 1
- `face_count` — number of faces detected
- `scene_category` — one of: landscape, indoor, portrait, food, city, nature, event, travel, document, art_meme

---

## Test Case 5: Filter Suggestions by Category

**Purpose:** Test category filtering.

```powershell
curl "http://localhost:8765/suggestions?category=junk" | python -m json.tool
```

**Expected output:** Only junk-category suggestions.

**Try each category:**
- `junk`
- `needs_review`
- `top_memories`
- `family_priority`
- `burst_pruning`

---

## Test Case 6: Blurry Photo Detection

**Purpose:** Verify blurry images are flagged.

**Setup:** Take 2 photos with the same camera:
- Photo A: Steady, in-focus shot (sharp)
- Photo B: Deliberately blurry (move camera during shot, or out of focus)

Place both in `C:\test-photos\`. Scan and check suggestions.

**Expected:**
- The blurry photo has `blur_score` < 0.2 (visible in suggestion details)
- Higher `junk_probability` than the sharp photo
- May appear in `junk` or `needs_review` depending on other factors

**Manual verification:**
```powershell
# Check specific file
curl http://localhost:8765/suggestions | python -c "
import sys, json
data = json.load(sys.stdin)
for cat, items in data.items():
    for item in items:
        if 'blurry' in item['file_name'].lower():
            print(f\"{item['file_name']}: blur={item.get('blur_score','?')}, junk={item.get('junk_probability','?')}\")
"
```

---

## Test Case 7: Low-Resolution / Small Photo Detection

**Purpose:** Verify tiny images are flagged as junk.

**Setup:** Create or find a very small image (< 200px on either side). Place in test folder. Scan.

**Expected:**
- The small image appears in `junk` category
- `reason` mentions low resolution
- `junk_probability` ≥ 0.6

---

## Test Case 8: Photo with Faces

**Purpose:** Verify face detection works.

**Setup:** Use a photo with 1-3 clearly visible faces (well-lit, front-facing).

**Check:**
```powershell
curl http://localhost:8765/suggestions | python -c "
import sys, json
data = json.load(sys.stdin)
for cat, items in data.items():
    for item in items:
        if item.get('face_count', 0) > 0:
            print(f\"FACES {item['face_count']}: {item['file_name']}\")
"
```

**Expected:**
- `face_count` > 0 for photos containing faces
- `max_face_priority` may be set (defaults to 1 for unknown faces)

**If no faces detected:**
- Ensure face is front-facing and well-lit
- Check server console for insightface model download/load messages

---

## Test Case 9: Burst / Near-Duplicate Photos

**Purpose:** Verify burst clustering groups similar photos.

**Setup:** Take 3-5 photos of the same subject within 1-2 seconds (smartphone burst mode). Place in test folder. Scan.

**Expected:**
- Some photos get `cluster_role: "pruned"` (visible in DB or suggestions)
- If pruning detected, they appear in `burst_pruning` category
- One photo is marked `hero`, one `backup`, rest `pruned`

**Check directly in DB (advanced):**
```powershell
# Install DB Browser for SQLite or use python:
python -c "
import sqlite3
conn = sqlite3.connect('photocurator.db')
for row in conn.execute('SELECT file_name, cluster_role, cluster_id FROM assets WHERE cluster_role IS NOT NULL'):
    print(f'{row[0]} -> {row[1]} (cluster: {row[2]})')
"
```

**If burst not detected:**
- Photos need timestamps within 2 seconds of each other
- Photos need similar perceptual hashes (pHash distance < 15)
- Use EXIF timestamps OR file modification times (EXIF preferred)

---

## Test Case 10: Empty Folder

**Purpose:** Verify the system handles empty input gracefully.

```powershell
mkdir C:\empty-test
curl -X POST http://localhost:8765/scan ^
  -H "Content-Type: application/json" ^
  -d '{"folder": "C:\\empty-test"}'
```

**Expected:** Scan completes successfully with zero total files.

```powershell
curl http://localhost:8765/summary | python -m json.tool
```

**Expected:** `{"total_assets": 0, "analyzed_assets": 0, ...}`

---

## Test Case 11: Invalid / Missing Folder

**Purpose:** Verify error handling for invalid paths.

```powershell
curl -X POST http://localhost:8765/scan ^
  -H "Content-Type: application/json" ^
  -d '{"folder": "C:\\nonexistent-folder"}'
```

**Expected:** Returns HTTP 500 or scan job status `failed` with error message.

---

## Test Case 12: Unsupported File Types

**Purpose:** Verify non-image files are silently skipped.

**Setup:** Place a `.txt`, `.pdf`, `.docx` file alongside images in the test folder.

**Expected:**
- `total_assets` only counts supported image files (.jpg, .jpeg, .png, .heic, .heif, .webp, .bmp)
- Unsupported files ignored (no errors)
- No crash

---

## Test Case 13: Corrupted Image

**Purpose:** Verify handling of corrupted/malformed image files.

**Setup:** Create a file with `.jpg` extension but random binary content:

```powershell
# Create corrupted image
powershell -Command "[System.IO.File]::WriteAllBytes('C:\test-photos\corrupt.jpg', (1..100))"
```

**Expected:**
- The file is detected by the scanner (extension matches)
- AI pipeline skips it gracefully (logged as error)
- No crash, remaining images processed normally

---

## Test Case 14: Large Folder (100+ Photos)

**Purpose:** Test performance and batching.

**Setup:** Gather 100+ photos in one folder. Scan.

**Expected:**
- All photos processed successfully
- Processing time roughly 2-10 seconds per image depending on CPU
- Memory stays stable (no leaks over time)
- Scan completes without timeout

**Monitor:**
```powershell
# Watch progress
while ($true) {
  curl http://localhost:8765/scan/1 | python -m json.tool
  Start-Sleep -Seconds 5
}
```

---

## Test Case 15: Rescan Same Folder

**Purpose:** Verify incremental scanning works.

**Setup:**
1. Place 5 photos in folder. Scan (completes with 5 assets).
2. Add 3 new photos to the same folder. Scan again.

**Expected:**
- Second scan creates a **new** scan job (new ID)
- Total files in second scan = 8 (all files)
- But only 3 newly processed (existing files marked as `pending`, pipeline skips them... actually for MVP full re-scan happens)

**Note for MVP:** Incremental scanning (comparing file paths + timestamps) is planned for Phase 7. In MVP, every scan re-processes all files. The `INSERT OR REPLACE` in the DB handles duplicates.

---

## Test Case 16: Screenshot / WhatsApp-like Image

**Purpose:** Verify heuristic junk detection for low-value image types.

**Setup:** Take a screenshot (Win+Printscreen). Place in test folder.

**Expected:**
- Screenshot may or may not be flagged as junk (no OCR in MVP)
- If screenshot has low color variance and low aesthetic score, it may appear in `junk`
- Otherwise it falls to `needs_review`

**Note:** OCR-based screenshot detection comes in Phase 2.

---

## Test Case 17: Photo with GPS Coordinates

**Purpose:** Verify EXIF GPS extraction.

**Setup:** Use a photo taken with a smartphone (phones typically embed GPS). Place in test folder. Scan.

**Check directly in DB:**
```powershell
python -c "
import sqlite3
conn = sqlite3.connect('photocurator.db')
for row in conn.execute('SELECT file_name, gps_lat, gps_lon FROM assets WHERE gps_lat IS NOT NULL'):
    print(f'{row[0]}: {row[1]}, {row[2]}')
"
```

**Expected:**
- `gps_lat` and `gps_lon` populated if the photo has GPS EXIF data
- Photos without GPS show NULL

---

## Test Case 18: Photo with Known Faces (Face Matching)

**Purpose:** Test face matching against known identities.

**Note:** Face labeling is a Phase 4 feature. For MVP, all faces are unknown (priority 1).

**Setup:** Place 2 photos of the same person in the folder. Scan.

**Check:**
```powershell
curl http://localhost:8765/suggestions | python -c "
import sys, json
data = json.load(sys.stdin)
for cat, items in data.items():
    for item in items:
        if item.get('face_count', 0) > 0:
            print(f\"{item['file_name']}: {item['face_count']} faces\")
"
```

**Expected:**
- Both photos show `face_count` > 0
- All faces have `identity_name: null` (unknown)
- If you manually assign names in the DB, re-running the scan auto-matches at >0.85 similarity

---

## Test Case 19: Scene Classification Accuracy

**Purpose:** Verify the heuristic scene classifier produces reasonable labels.

**Setup:** Use photos with clearly identifiable content:
- A beach/ocean photo → should be `landscape` or `nature`
- A selfie → should be `portrait`
- A plate of food → should be `food`
- A screenshot of text → should be `document`

**Check:**
```powershell
curl http://localhost:8765/suggestions | python -c "
import sys, json
data = json.load(sys.stdin)
for cat, items in data.items():
    for item in items:
        print(f\"{item['file_name']}: scene={item['scene_category']}, aesthetic={item['aesthetic_score']:.2f}\")
"
```

**Expected:** Scene categories should be broadly correct. The heuristic classifier is simplified for MVP — don't expect perfect results for edge cases. Phase 2 replaces this with CLIP.

---

## Test Case 20: Multiple Scan Jobs

**Purpose:** Test concurrent scan jobs.

**Setup:**
```powershell
# Start two scans on different folders
curl -X POST http://localhost:8765/scan ^
  -H "Content-Type: application/json" ^
  -d '{"folder": "C:\\test-photos-a"}'

curl -X POST http://localhost:8765/scan ^
  -H "Content-Type: application/json" ^
  -d '{"folder": "C:\\test-photos-b"}'
```

**Expected:**
- Two scan jobs created with different IDs
- Both can be polled independently
- Both complete successfully

---

## Test Results Template

Copy this table to track your results:

| # | Test Case | Status | Notes |
|---|---|---|---|
| 1 | Server Health | | |
| 2 | Scan Mixed Photos | | |
| 3 | Summary Dashboard | | |
| 4 | View Suggestions | | |
| 5 | Filter by Category | | |
| 6 | Blurry Photo | | |
| 7 | Low Resolution | | |
| 8 | Photo with Faces | | |
| 9 | Burst Detection | | |
| 10 | Empty Folder | | |
| 11 | Invalid Folder | | |
| 12 | Unsupported Types | | |
| 13 | Corrupted Image | | |
| 14 | Large Folder (100+) | | |
| 15 | Rescan | | |
| 16 | Screenshot | | |
| 17 | GPS Data | | |
| 18 | Face Matching | | |
| 19 | Scene Classification | | |
| 20 | Multiple Scans | | |
