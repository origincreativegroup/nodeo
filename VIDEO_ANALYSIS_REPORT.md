# Video Analysis Implementation Report for jspow

## Executive Summary

The jspow application is an AI-powered image and video file renaming and organization tool. It supports both images and videos, with video analysis integrated through a multi-stage pipeline involving FFprobe for technical metadata extraction and LLaVA vision model for semantic analysis.

---

## 1. VIDEO ANALYSIS ARCHITECTURE

### 1.1 Overall Flow

```
Video Upload → File Validation → Storage → Metadata Extraction → AI Analysis → Database Storage
     ↓              ↓                 ↓              ↓                    ↓              ↓
   /upload      [mp4,mov,avi]    /originals    FFprobe            LLaVA Vision   Images table
                                 /working      + Magick           Model (Ollama) with analysis
```

### 1.2 Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **Media Metadata Service** | `app/services/media_metadata.py` | Extracts technical metadata (resolution, duration, codec, frame rate) |
| **LLaVA Client** | `app/ai/llava_client.py` | Semantic analysis using vision model (description, tags, objects, scene) |
| **Metadata Service** | `app/services/metadata_service.py` | High-level orchestrator for AI-powered metadata generation |
| **Main API** | `main.py` | HTTP endpoints for upload, analysis, and batch operations |
| **Models** | `app/models.py` | Database schema for Image, MediaMetadata, and related tables |

---

## 2. VIDEO INPUT TO ANALYSIS FLOW

### 2.1 Upload Phase (`POST /api/images/upload`)

**File Processing:**
```
1. Receive uploaded video file
2. Validate extension (mp4, mov, avi, mkv, webm)
3. Read file content into memory
4. Store in two locations:
   - /app/storage/originals/ (backup)
   - /app/storage/working/ (processing)
5. Create metadata sidecar in /app/storage/metadata/
```

**Database Recording:**
```python
# Creates Image record with:
- original_filename: str (preserved upload filename)
- current_filename: str (may change with renaming)
- file_path: str (location on disk)
- file_size: int (bytes)
- mime_type: str (e.g., "video/mp4")
- media_type: Enum (MediaType.VIDEO)
- storage_type: Enum (StorageType.LOCAL)
- upload_batch_id: ForeignKey (groups uploads)
```

### 2.2 Metadata Extraction Phase

**Technical Metadata Extraction (FFprobe)**

*File: `app/services/media_metadata.py`*

```python
async def _probe_video(self, path: Path) -> Dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name",
        "-show_entries", "format=duration,format_name",
        "-of", "json",
        str(path),
    ]
    # Executes ffprobe and parses JSON output
```

**Extracted Technical Data:**
- `width`: int (pixels)
- `height`: int (pixels)
- `duration_s`: float (seconds)
- `frame_rate`: float (fps, parsed from numerator/denominator)
- `codec`: str (e.g., "h264", "hevc", "vp9")
- `format`: str (e.g., "mov,mp4,m4a,3gp,3g2,mj2")

**Caching Strategy:**
- Checks database for cached metadata using file path + mtime
- If file hasn't changed (same mtime), returns cached record
- Otherwise, probes file and stores in `media_metadata` table

### 2.3 AI Analysis Phase

**Two Analysis Methods Available:**

#### Method 1: Fast Extract Metadata (Default)
*File: `app/ai/llava_client.py` - `_extract_metadata_fast()`*

```
Single API call to Ollama/LLaVA with structured JSON prompt
Response Time: 1-2 seconds per video
```

**Prompt:**
```
Analyze this [video/image] in detail and provide JSON with:
{
  "description": "2-3 sentence description",
  "tags": ["5-10", "relevant", "keywords"],
  "objects": ["main", "visible", "objects"],
  "scene": "scene type (1-2 words)",
  "mood": "optional atmosphere descriptor",
  "colors": ["dominant", "color", "palette"]
}
```

**Error Handling:**
```python
try:
    # Parse JSON response
    metadata = json.loads(content)
except json.JSONDecodeError as e:
    logger.warning(f"Failed to parse JSON: {e}")
    # Fallback to legacy 4-call method
    return await self._extract_metadata_legacy(image_path)
```

#### Method 2: Legacy Fallback Method
*File: `app/ai/llava_client.py` - `_extract_metadata_legacy()`*

```
Four sequential API calls:
1. Get description (2-3 sentences)
2. Extract tags (comma-separated)
3. Identify objects (comma-separated)
4. Determine scene type (1-2 words)

Response Time: 4-8 seconds per video
Used only if fast method fails
```

### 2.4 Batch Analysis

**Concurrent Processing with Semaphore:**
```python
async def batch_analyze(
    image_paths: List[str],
    concurrent: bool = True,
    max_concurrent: int = 5
):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async with semaphore:
        # Process up to 5 images simultaneously
        metadata = await self.extract_metadata(image_path)
```

**Performance:**
- Sequential (old): 50 videos = 200-400 seconds
- Concurrent (new): 50 videos = 20-40 seconds
- **Improvement: 5-10x faster**

### 2.5 Analysis Results Storage

**Database Schema (Image table):**
```python
ai_description: Text          # Main descriptive text
ai_tags: JSON                 # Array of keyword tags
ai_objects: JSON              # Detected objects
ai_scene: String(200)         # Scene type (indoor, outdoor, etc.)
ai_embedding: JSON            # Vector embedding (for similarity)
analyzed_at: DateTime         # Timestamp of analysis
```

---

## 3. POTENTIAL ERRORS AND FAILURE MODES

### 3.1 File System Errors

| Error | Cause | Handling | Recovery |
|-------|-------|----------|----------|
| `FileNotFoundError` | Video file deleted or moved | Check file exists before upload | Re-upload file |
| `PermissionError` | Insufficient access rights | Check file permissions | Run with proper permissions |
| `ENOSPC` | Disk full | Monitor storage space | Free up disk space |
| `EINVAL` | Invalid file path | Validate paths | Clean up filenames |

**Code Location:** `main.py` lines 324-426, 1304-1361

### 3.2 FFprobe Errors

| Error | Cause | Handling | Recovery |
|-------|-------|----------|----------|
| `FileNotFoundError` | FFprobe not installed | Log warning, skip probe | Install ffmpeg suite |
| `RuntimeError` | FFprobe execution failed | Log error with stderr | Check video file integrity |
| `json.JSONDecodeError` | Invalid JSON output | Log error, use cached data | Try with working copy |
| `TimeoutError` | Command takes too long | 5-second timeout by default | Increase timeout |

**Code Location:** `app/services/media_metadata.py` lines 199-242

```python
except FileNotFoundError as exc:
    logger.error("ffprobe is required but was not found: %s", exc)
    return {}
except RuntimeError as exc:
    logger.error("ffprobe failed for %s: %s", path, exc)
    return {}
except json.JSONDecodeError as exc:
    logger.error("ffprobe returned invalid JSON for %s: %s", path, exc)
    return {}
```

### 3.3 AI Model Errors (Ollama/LLaVA)

| Error | Cause | Handling | Recovery |
|-------|-------|----------|----------|
| Connection refused | Ollama not running | Log error, raise exception | Start Ollama service |
| Model not loaded | LLaVA model unavailable | Request fails to load | Download/configure model |
| Timeout (120s default) | Model processing too slow | Log timeout error | Increase timeout or use simpler model |
| JSON parse error | Model output invalid JSON | Fall back to legacy method | Use 4-call method |
| Out of memory | Model exceeds VRAM | Server error returned | Reduce concurrent limit |

**Configuration:**
```python
# app/config.py
ollama_host: str = "http://192.168.50.248:11434"
ollama_model: str = "llava"
ollama_timeout: int = 120  # seconds
```

**Code Location:** `app/ai/llava_client.py` lines 155-269

```python
async def _extract_metadata_fast(self, image_path: str) -> Dict:
    try:
        client = ollama.Client(host=self.host)
        response = client.chat(
            model=self.model,
            messages=[{...}],
            options={'temperature': 0.3, 'num_predict': 300}
        )
        content = response['message']['content'].strip()
        
        # Try JSON parsing
        metadata = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON: {e}")
        # Fallback to legacy method
        return await self._extract_metadata_legacy(image_path)
    except Exception as e:
        logger.error(f"Error in fast extraction: {e}")
        # Fallback to legacy method
        return await self._extract_metadata_legacy(image_path)
```

### 3.4 Database Errors

| Error | Cause | Handling | Recovery |
|-------|-------|----------|----------|
| Connection pool exhausted | Too many concurrent requests | Log critical error | Wait for connections to free |
| Constraint violation | Duplicate unique values | Raise validation error | Use unique identifiers |
| Transaction timeout | Long-running operation | Rollback transaction | Retry operation |
| Schema mismatch | Column doesn't exist | Migration required | Run alembic migrations |

**Code Location:** `main.py` lines 454-473

```python
try:
    metadata = await llava_client.extract_metadata(image.file_path)
    image.ai_description = metadata['description']
    image.ai_tags = metadata['tags']
    image.ai_objects = metadata['objects']
    image.ai_scene = metadata['scene']
    image.analyzed_at = datetime.utcnow()
    await db.commit()
except Exception as e:
    logger.error(f"Error analyzing image {image_id}: {e}")
    raise HTTPException(status_code=500, detail=str(e))
```

### 3.5 Batch Processing Errors

**Partial Failure Handling:**
```python
# Each item processed independently
for image_id in image_ids:
    try:
        metadata = await llava_client.extract_metadata(image.file_path)
        # Update database
    except Exception as e:
        logger.error(f"Error analyzing image {image_id}: {e}")
        results.append({
            "image_id": image_id,
            "success": False,
            "error": str(e)
        })

# Returns summary:
{
    "total": 50,
    "succeeded": 48,
    "results": [...]
}
```

**Code Location:** `main.py` lines 526-610

### 3.6 Video-Specific Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| Corrupted file | FFprobe returns no streams | Verify with `ffmpeg -v` |
| Unsupported codec | FFprobe can't read codec | Convert to supported format |
| Frame rate parsing | Fails on non-standard rates | Uses formula: numerator/denominator |
| Missing audio track | Analysis works on video track | Ignores audio, analyzes video |
| Very large file | Timeout or memory issues | Increase timeout or reduce batch size |
| Non-seekable stream | Can't extract frames | Use standard container format |

**Frame Rate Parsing:**
```python
def _parse_frame_rate(value: Any) -> Optional[float]:
    if isinstance(value, str) and "/" in value:
        try:
            numerator, denominator = value.split("/", 1)
            if float(denominator) == 0:
                return None
            return float(numerator) / float(denominator)
        except (ValueError, ZeroDivisionError):
            return None
    return float(value) if isinstance(value, (int, float)) else None
```

---

## 4. ERROR HANDLING AND LOGGING

### 4.1 Error Handler Service

**File:** `app/services/error_handler.py`

**Error Categories:**
- `NETWORK` - Connection/timeout issues
- `VALIDATION` - Invalid input data
- `FILE_SYSTEM` - File operations
- `PERMISSION` - Access denied
- `AI_MODEL` - Ollama/LLaVA failures
- `STORAGE` - Cloud storage issues
- `DATABASE` - Database errors
- `UNKNOWN` - Uncategorized

**Error Severity:**
- `INFO` - Informational
- `WARNING` - Minor issue
- `ERROR` - Standard error
- `CRITICAL` - Severe failure

### 4.2 Logging Configuration

**File:** `app/debug_utils.py`

```python
# Enhanced logging with:
setup_enhanced_logging(log_level="DEBUG" if settings.debug else "INFO")

# Log output:
logger.info(f"Analyzing image: {image_path}")
logger.error(f"Error analyzing image {image_id}: {e}")
logger.warning("Failed to rebuild AI groupings: %s", exc)
```

**Log Files:**
- `logs/jspow.log` - Application logs
- `logs/errors.log` - Error-specific logs

### 4.3 Timeout Configuration

**Default Timeouts:**
```python
# Ollama AI model
ollama_timeout: int = 120  # seconds

# FFprobe (inherits from subprocess timeout)
# No explicit timeout, but system-level timeouts apply

# CloudFlare Stream upload
timeout=600.0  # 10 minutes for large videos

# HTTP requests
timeout=aiohttp.ClientTimeout(total=5)  # 5 seconds

# Overall process
process_timeout_seconds: int = 300  # 5 minutes
```

---

## 5. MONITORING AND DEBUG ENDPOINTS

### 5.1 Health Check

**Endpoint:** `GET /health`
```json
{
  "status": "healthy",
  "app": "jspow",
  "version": "1.0.0"
}
```

### 5.2 Full System Health

**Endpoint:** `GET /debug/health-full`
```json
{
  "timestamp": "2025-11-07T10:30:00",
  "overall_status": "healthy|degraded",
  "services": {
    "database": {"status": "connected"},
    "ollama": {"status": "connected"},
    "nextcloud": {"status": "connected"}
  }
}
```

### 5.3 Recent Logs

**Endpoints:**
- `GET /debug/logs/recent?lines=50` - Application logs
- `GET /debug/errors/recent?lines=50` - Error logs

**Debug System Info:**
- `GET /debug/system` - Full system information

---

## 6. VIDEO ANALYSIS ENDPOINTS

### 6.1 Single Video Analysis

**Endpoint:** `POST /api/images/{image_id}/analyze`

**Request:** Image ID
**Response:**
```json
{
  "success": true,
  "image_id": 123,
  "analysis": {
    "description": "A person jogging in a park...",
    "tags": ["outdoor", "exercise", "sports", ...],
    "objects": ["person", "trees", "grass"],
    "scene": "outdoor"
  },
  "project_classification": {
    "assigned_project_id": 5,
    "confidence": 0.85
  }
}
```

### 6.2 Batch Analysis

**Endpoint:** `POST /api/images/batch-analyze`

**Request:**
```json
{
  "image_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "total": 5,
  "succeeded": 4,
  "results": [
    {"image_id": 1, "success": true, "analysis": {...}},
    {"image_id": 2, "success": true, "analysis": {...}},
    {"image_id": 3, "success": false, "error": "File not found"}
  ],
  "project_classifications": [...]
}
```

### 6.3 Error Responses

All errors follow this format:
```json
{
  "detail": "Error message",
  "status_code": 500,
  "category": "ai_model",
  "severity": "error"
}
```

---

## 7. CONFIGURATION FOR VIDEO PROCESSING

**File:** `app/config.py`

```python
# Allowed video extensions
allowed_video_extensions: str = "mp4,mov,avi,mkv,webm"

# Allowed image extensions (for comparison)
allowed_image_extensions: str = "jpg,jpeg,png,gif,webp,bmp,tiff"

# Upload limits
max_batch_size: int = 50
max_upload_size_mb: int = 100
process_timeout_seconds: int = 300

# AI Model
ollama_host: str = "http://192.168.50.248:11434"
ollama_model: str = "llava"
ollama_timeout: int = 120
```

---

## 8. DATA FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│                      USER UPLOADS VIDEO                      │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼─────────┐
                    │ Validate Extension│
                    │(mp4,mov,avi,...) │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ Save to Disk      │
                    │/originals/working│
                    └────────┬─────────┘
                             │
        ┌────────────────────┴────────────────────┐
        │                                          │
    ┌───▼────────┐                         ┌──────▼──────┐
    │ FFprobe    │                         │ Metadata    │
    │ Extract:   │                         │ Sidecar     │
    │ - Resolution                         │ Metadata    │
    │ - Duration │                         │ (JSON)      │
    │ - Codec    │                         └─────────────┘
    │ - FPS      │
    └───┬────────┘
        │
    ┌───▼────────────────────────────────┐
    │ Store Technical Metadata            │
    │ in media_metadata table             │
    └───┬────────────────────────────────┘
        │
    ┌───▼────────────────────────────────┐
    │ Create Image DB Record              │
    │ with media_type = VIDEO             │
    └───┬────────────────────────────────┘
        │
        │ (User clicks "Analyze")
        │
    ┌───▼────────────────────────────────┐
    │ Send to Ollama/LLaVA                │
    │ - Video frame or first frame         │
    │ - Structured JSON prompt            │
    └───┬────────────────────────────────┘
        │
    ┌───▼────────────────────────────────┐
    │ If JSON parsing fails:              │
    │ → Fallback to legacy 4-call method  │
    └───┬────────────────────────────────┘
        │
    ┌───▼────────────────────────────────┐
    │ Store AI Analysis:                  │
    │ - ai_description                    │
    │ - ai_tags                           │
    │ - ai_objects                        │
    │ - ai_scene                          │
    │ - analyzed_at (timestamp)           │
    └───┬────────────────────────────────┘
        │
    ┌───▼────────────────────────────────┐
    │ Optional: Project Classification    │
    │ and Auto-Grouping                   │
    └───┬────────────────────────────────┘
        │
    ┌───▼────────────────────────────────┐
    │ ANALYSIS COMPLETE                   │
    │ Video ready for renaming/grouping   │
    └────────────────────────────────────┘
```

---

## 9. POTENTIAL IMPROVEMENTS

### Currently Missing:

1. **Video Frame Extraction**
   - Currently analyzes video without extracting specific frames
   - No OpenCV/ffmpeg frame extraction
   - Could extract keyframe or multiple frames for better analysis

2. **Video Duration-Aware Analysis**
   - Doesn't use duration in analysis prompts
   - Could customize prompts based on video length

3. **Retry Mechanism**
   - No built-in retry with backoff for transient failures
   - Relies on client-side retry logic

4. **Progress Tracking**
   - No progress updates during long-running analyses
   - Could use WebSocket or polling for status

5. **Caching**
   - No caching of identical file analyses
   - Could cache results for files with same content hash

---

## 10. SUMMARY TABLE

| Aspect | Status | Details |
|--------|--------|---------|
| **Video Upload** | ✅ Complete | Validates extensions, stores to disk and DB |
| **Technical Metadata** | ✅ Complete | FFprobe extracts resolution, duration, codec, FPS |
| **AI Analysis** | ✅ Complete | LLaVA vision model analyzes semantic content |
| **Error Handling** | ✅ Complete | Comprehensive categorization and logging |
| **Batch Processing** | ✅ Complete | Concurrent processing with 5-10x speedup |
| **Fallback Mechanism** | ✅ Complete | Falls back to legacy 4-call method if JSON fails |
| **Timeout Protection** | ✅ Complete | 120s Ollama timeout, 300s process timeout |
| **Database Caching** | ✅ Complete | Caches metadata based on file mtime |
| **Video Frame Extraction** | ❌ Not implemented | Would improve accuracy for video analysis |
| **Stream Processing** | ❌ Not implemented | Large files processed synchronously |

