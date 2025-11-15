# JSPOW Codebase Overview for CSV Upload Feature Implementation

## 1. PROJECT STRUCTURE

### Overall Architecture
JSPOW is a **monolithic application** with a clear frontend/backend separation:

```
/home/user/jspow/
├── frontend/                 # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── components/       # 17 React components
│   │   ├── pages/           # 6 main pages (Dashboard, RenameManager, etc.)
│   │   ├── services/        # api.ts - Axios API client
│   │   ├── context/         # AppContext.tsx - Global state
│   │   ├── utils/           # Utility functions
│   │   └── hooks/           # Custom React hooks
│   └── package.json
│
├── app/                      # FastAPI Backend (Python)
│   ├── routers/             # API endpoints (v2)
│   │   ├── folders.py       # Watched folder management
│   │   ├── suggestions.py   # Rename suggestions
│   │   ├── activity.py      # Activity logging & export
│   │   └── websocket.py     # Real-time updates
│   ├── services/            # Business logic
│   │   ├── folder_watcher.py     # Automated folder monitoring
│   │   ├── project_service.py    # Project management
│   │   ├── grouping.py           # Image grouping logic
│   │   ├── media_metadata.py     # Media analysis
│   │   └── [7+ other services]
│   ├── storage/             # Storage backends
│   │   ├── layout.py        # Local storage layout manager
│   │   ├── nextcloud.py     # Nextcloud integration
│   │   ├── cloudflare.py    # Cloudflare R2 & Stream
│   │   └── [metadata management]
│   ├── ai/                  # AI integration
│   │   ├── llava_client.py  # LLaVA vision model client
│   │   └── project_classifier.py
│   ├── models.py            # SQLAlchemy database models
│   ├── config.py            # Settings (Pydantic)
│   ├── database.py          # Database setup
│   └── __init__.py
│
├── main.py                  # FastAPI application entry point (2312 lines)
├── migrations/              # Alembic database migrations
├── tests/                   # Pytest test suite
├── requirements.txt         # Python dependencies
└── docker-compose.yml       # Container orchestration
```

---

## 2. FILE UPLOAD HANDLING

### Current Upload Mechanism

**Endpoint:** `POST /api/images/upload`
- **Location:** `/home/user/jspow/main.py` (lines 307-466)
- **Method:** FastAPI `UploadFile` with multipart form data
- **Request:** Multiple files as `files: List[UploadFile] = File(...)`
- **Response:** UploadResponse containing results array

### Upload Flow

```python
# 1. Create UploadBatch record
upload_batch = UploadBatch(
    label=f"Upload {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
    source="web",
    attributes={"total_expected": len(files)}
)

# 2. Create ImageGroup for batch tracking
upload_group = ImageGroup(
    name=upload_label,
    group_type=GroupType.UPLOAD_BATCH,
    upload_batch_id=upload_batch.id
)

# 3. For each file:
# - Validate extension against allowed_image_exts / allowed_video_exts
# - Read file content
# - Save to storage layout (originals + working copies)
# - Write metadata JSON sidecar
# - Create Image database record
# - Associate with upload_batch and upload_group
```

### Storage Layout Structure
**Location:** `/home/user/jspow/app/storage/layout.py`

Files are organized as:
```
/app/storage/{type}/{year}/{project}/{asset_id}/{filename}
```

- `type`: "originals" | "working" | "exports" | "metadata"
- `year`: 4-digit upload year
- `project`: slugified project code (default: "general")
- `asset_id`: UUID hex string generated at upload

**Key Classes:**
- `StorageManager` - Central class for file operations
- Methods: `write_file()`, `write_metadata()`, `read_metadata()`, `generate_manifest()`

### File Validation
```python
# From main.py lines 352-362
ext = Path(file.filename).suffix.lower().lstrip('.')
is_image = ext in settings.allowed_image_exts
is_video = ext in settings.allowed_video_exts

if not (is_image or is_video):
    raise error "Invalid file type"
```

**Allowed Extensions (from config.py):**
- Images: jpg, jpeg, png, gif, webp, bmp, tiff
- Videos: mp4, mov, avi, mkv, webm
- Max batch size: 50 files
- Max file size: 100 MB

---

## 3. ASSET MANAGEMENT & STORAGE

### Database Models

**Image (Asset Record)**
```python
class Image(Base):
    id: Integer (primary key)
    original_filename: String(500)
    current_filename: String(500)
    file_path: String(1000)        # Working copy path
    file_size: Integer
    mime_type: String(100)
    media_type: Enum(IMAGE|VIDEO)
    
    # Dimensions
    width, height: Integer
    duration_s, frame_rate, codec, media_format: (for videos)
    
    # AI Analysis
    ai_description: Text
    ai_tags: JSON (list of tags)
    ai_objects: JSON (detected objects)
    ai_scene: String(200)
    ai_embedding: JSON (vector)
    analyzed_at: DateTime
    
    # Storage
    storage_type: Enum(LOCAL|NEXTCLOUD|R2|STREAM)
    nextcloud_path: String(1000)
    r2_key: String(1000)
    stream_id: String(200)
    
    # Relationships
    upload_batch_id: ForeignKey(UploadBatch)
    project_id: ForeignKey(Project)
    metadata_id: ForeignKey(MediaMetadata)
    
    # v2 Relationships
    rename_suggestions: relationship(RenameSuggestion)
    activity_logs: relationship(ActivityLog)
    asset_tags: relationship(AssetTag)
    groups: relationship(ImageGroup, secondary=image_group_associations)
```

**UploadBatch**
```python
class UploadBatch(Base):
    id: Integer (primary key)
    label: String(255)           # "Upload 2025-01-15 14:30"
    source: String(255)          # "web" | "folder_watcher" | etc.
    attributes: JSON             # {total_expected, image_count, ...}
    created_at: DateTime
    
    # Relationships
    images: relationship(Image)
    group: relationship(ImageGroup)
```

**ImageGroup & ImageGroupAssociation**
```python
class ImageGroup(Base):
    id: Integer (primary key)
    name: String(255)
    group_type: Enum(AI_TAG_CLUSTER | AI_SCENE_CLUSTER | MANUAL_COLLECTION | UPLOAD_BATCH)
    attributes: JSON
    is_user_defined: Boolean
    upload_batch_id: ForeignKey
    project_id: ForeignKey
    
    # Relationships
    images: relationship(Image, secondary=image_group_associations)

class ImageGroupAssociation(Base):
    group_id: Integer (FK, primary)
    image_id: Integer (FK, primary)
    attributes: JSON
    created_at: DateTime
```

**MediaMetadata** (cached technical metadata)
```python
class MediaMetadata(Base):
    file_path: String(1000) [unique]
    file_mtime: Float
    media_type: Enum(IMAGE|VIDEO)
    width, height: Integer
    duration_s, frame_rate: Float
    codec, media_format: String
    raw_metadata: JSON
    
    # Relationships
    assets: relationship(Image)
```

### Asset Listing Endpoint
**Endpoint:** `GET /api/images` (main.py lines 1793-1855)

**Parameters:**
- `skip`: Pagination offset
- `limit`: Page size (default 100)
- `group_type`: Filter by group type
- `group_id`: Filter by group ID
- `upload_batch_id`: Filter by upload batch
- `project_id`: Filter by project
- `analyzed_only`: Only analyzed images

**Response:** Paginated array of Image objects with full metadata

---

## 4. APIs & ENDPOINTS

### Comprehensive Endpoint Map

#### Image Management
```
POST   /api/images/upload                 - Upload multiple images
POST   /api/images/{id}/analyze           - Single image AI analysis
POST   /api/images/batch-analyze          - Batch image analysis
GET    /api/images                        - List all images with filters
GET    /api/images/{id}/thumbnail         - Get thumbnail
PATCH  /api/images/bulk/tags             - Bulk tag management
```

#### Rename Operations
```
POST   /api/rename/preview                - Preview rename with template
POST   /api/rename/apply                  - Apply template-based rename
POST   /api/rename/bulk                   - Bulk find/replace rename
POST   /api/rename/auto                   - Auto-rename using AI (experimental)
```

#### Template Management
```
GET    /api/templates                     - List all templates
POST   /api/templates                     - Create template
GET    /api/templates/{id}                - Get template
PUT    /api/templates/{id}                - Update template
DELETE /api/templates/{id}                - Delete template
POST   /api/templates/{id}/favorite       - Mark as favorite
POST   /api/templates/import              - Bulk import templates
GET    /api/templates/export              - Export templates
```

#### Grouping & Organization
```
GET    /api/groupings                     - List all groups
POST   /api/groupings/rebuild             - Rebuild AI groups
POST   /api/groupings/manual              - Create manual group
POST   /api/groupings/{id}/assign         - Assign images to group
```

#### Project Management
```
POST   /api/projects                      - Create project
GET    /api/projects                      - List projects
GET    /api/projects/{id}                 - Get project
PATCH  /api/projects/{id}                 - Update project
DELETE /api/projects/{id}                 - Delete project
POST   /api/projects/{id}/assign-assets   - Assign images to project
DELETE /api/projects/{id}/remove-assets   - Remove images from project
GET    /api/projects/{id}/stats           - Project statistics
POST   /api/projects/{id}/rename/preview  - Project-aware rename preview
POST   /api/projects/{id}/rename/apply    - Apply project-aware rename
```

#### Storage Operations
```
POST   /api/storage/nextcloud/upload      - Upload to Nextcloud
POST   /api/storage/r2/upload             - Upload to Cloudflare R2
```

#### Metadata Management
```
POST   /api/metadata/{id}/sidecar         - Save metadata sidecar
GET    /api/metadata/{id}/sidecar         - Download metadata sidecar
```

#### v2 Folder Monitoring (NEW)
```
POST   /api/v2/folders                    - Add watched folder
GET    /api/v2/folders                    - List watched folders
GET    /api/v2/folders/{id}               - Get folder details
PATCH  /api/v2/folders/{id}               - Update folder config
DELETE /api/v2/folders/{id}               - Remove watched folder
POST   /api/v2/folders/{id}/rescan        - Manual rescan
GET    /api/v2/folders/{id}/progress      - Scan progress

GET    /api/v2/suggestions                - List rename suggestions
GET    /api/v2/suggestions/{id}           - Get suggestion
PATCH  /api/v2/suggestions/{id}           - Update suggestion
POST   /api/v2/suggestions/{id}/approve   - Approve suggestion
POST   /api/v2/suggestions/{id}/reject    - Reject suggestion
POST   /api/v2/suggestions/batch-approve  - Batch approve
POST   /api/v2/suggestions/batch-reject   - Batch reject

GET    /api/v2/activity                   - List activity logs
GET    /api/v2/activity/stats             - Activity statistics
GET    /api/v2/activity/export            - Export as CSV/JSON (EXISTING CSV EXPORT!)
DELETE /api/v2/activity/cleanup           - Cleanup old logs

WS     /api/v2/ws/progress                - WebSocket for real-time updates
GET    /api/v2/ws/status                  - WebSocket status
```

---

## 5. FRAMEWORKS & LIBRARIES

### Backend Dependencies (Python)
**Location:** `/home/user/jspow/requirements.txt`

| Category | Libraries |
|----------|-----------|
| **Web Framework** | FastAPI 0.109.0, Uvicorn 0.27.0 |
| **Database** | SQLAlchemy 2.0.25, asyncpg 0.29.0, Alembic 1.13.1 |
| **Caching** | Redis 5.0.1, aioredis 2.0.1 |
| **AI/ML** | Ollama 0.1.6 (LLaVA vision model) |
| **Storage** | boto3 1.34.34 (AWS S3/R2), webdav4 0.9.8 (Nextcloud), aiofiles 23.2.1 |
| **Image Processing** | Pillow 10.2.0, python-magic 0.4.27 |
| **Auth/Security** | python-jose 3.3.0, passlib 1.7.4, cryptography 42.0.0 |
| **Utilities** | Pydantic 2.5.3, pydantic-settings 2.1.0, httpx 0.25.2, python-dateutil 2.8.2 |
| **Background Tasks** | APScheduler 3.10.4 |
| **Folder Monitoring** | Watchdog 4.0.0 |
| **WebSockets** | websockets 12.0 |
| **Testing** | pytest 7.4.4, pytest-asyncio 0.23.3 |

### Frontend Dependencies (TypeScript/React)
**Location:** `/home/user/jspow/frontend/package.json`

| Category | Libraries |
|----------|-----------|
| **UI Framework** | React 18.2.0, React Router 6.20.0 |
| **Build Tool** | Vite 5.0.8, TypeScript 5.2.2 |
| **Styling** | Tailwind CSS 3.3.6 |
| **HTTP Client** | Axios 1.6.2 |
| **Icons** | lucide-react 0.294.0 |
| **Notifications** | react-hot-toast 2.4.1 |
| **Dev Tools** | ESLint, TypeScript, Vite plugins |

---

## 6. EXISTING CSV HANDLING & FILE PROCESSING

### CSV Export Feature (ALREADY EXISTS!)
**Location:** `/home/user/jspow/app/routers/activity.py` (lines 187-265)

**Endpoint:** `GET /api/v2/activity/export`
**Parameters:**
- `format`: "csv" or "json"
- `days`: Number of days to include (default 30)

**CSV Columns:**
```
ID, Action Type, Status, Original Filename, New Filename, Folder Path, Error Message, Created At
```

**Implementation Details:**
```python
import csv
import io

# Uses Python's built-in csv module
output = io.StringIO()
writer = csv.writer(output)

# Writes headers and data rows
# Returns Response with:
# - media_type="text/csv"
# - filename=activity_log_{YYYYMMDD}.csv
# - Content-Disposition header for download
```

### File Processing Capabilities

**Media Metadata Analysis** (services/media_metadata.py)
- Extract dimensions, duration, codec from files
- MIME type detection (python-magic)
- Caching of expensive operations

**Image Analysis with Ollama**
- AI description generation
- Tag extraction
- Object detection
- Scene classification
- Embedding vectors for similarity search

**Metadata Sidecar System** (main.py lines 1421-1500)
- JSON metadata stored alongside asset
- Includes title, description, alt text, tags
- Downloadable sidecar files

---

## 7. IMPLEMENTATION RECOMMENDATIONS FOR CSV UPLOAD FEATURE

### Key Considerations

1. **CSV Format Expected:**
   - Headers identifying asset metadata (filename, project, tags, description, etc.)
   - Each row represents one asset to import or find

2. **Integration Points:**
   - Leverage existing `UploadBatch` model to group CSV-sourced assets
   - Add CSV-specific import logic to routers (new endpoint needed)
   - Extend `ActivityLog` to track CSV import operations

3. **Database Schema:**
   - New model: `CSVImportJob` to track bulk import status
   - Extend `ActivityLog.action_type` enum with CSV-related actions

4. **Storage Backend:**
   - Reuse `storage_manager` from layout.py for file placement
   - Same metadata sidecar approach

5. **API Design Pattern:**
   - `POST /api/csv/import` - Upload CSV and return preview
   - `POST /api/csv/import/{job_id}/confirm` - Confirm and start import
   - `GET /api/csv/import/{job_id}/progress` - Track progress via WebSocket
   - `POST /api/csv/search` - Search assets based on CSV criteria

6. **Frontend Integration:**
   - Add CSV upload component (reuse file upload UI)
   - Preview table before import
   - Real-time progress tracking via WebSocket
   - Result summary with success/error counts

---

## 8. RELATED FILES TO REVIEW

### Critical for CSV Implementation
- `/home/user/jspow/main.py` - API structure and upload endpoint pattern
- `/home/user/jspow/app/models.py` - Data models to extend
- `/home/user/jspow/app/routers/activity.py` - CSV export implementation reference
- `/home/user/jspow/app/storage/layout.py` - File storage management
- `/home/user/jspow/app/services/project_service.py` - Project/asset relationships

### Frontend Reference
- `/home/user/jspow/frontend/src/pages/RenameManager.tsx` - Main UI layout
- `/home/user/jspow/frontend/src/services/api.ts` - API call patterns
- `/home/user/jspow/frontend/src/context/AppContext.tsx` - Global state management

### Configuration
- `/home/user/jspow/app/config.py` - Settings and allowed file types
- `/home/user/jspow/.env.example` - Environment configuration template

---

## 9. DATABASE SCHEMA RELATIONSHIPS

```
projects
  ├─ (1:N) images
  └─ (1:N) image_groups

images
  ├─ (N:1) projects
  ├─ (N:1) upload_batches
  ├─ (N:N) image_groups (via image_group_associations)
  ├─ (N:1) media_metadata
  ├─ (1:N) rename_suggestions
  ├─ (1:N) activity_logs
  └─ (1:N) asset_tags (via asset_tags)

upload_batches
  ├─ (1:N) images
  └─ (1:1) image_group

image_groups
  ├─ (N:N) images (via image_group_associations)
  ├─ (N:1) projects
  └─ (N:1) upload_batches

watched_folders (v2)
  ├─ (1:N) rename_suggestions
  └─ (1:N) activity_logs

rename_suggestions (v2)
  ├─ (N:1) watched_folder
  ├─ (N:1) images
  └─ -> activity_logs

activity_log (v2)
  ├─ (N:1) watched_folder
  └─ (N:1) images
```

---

## 10. CURRENT GIT BRANCH INFO

**Current Branch:** `claude/csv-asset-upload-feature-01Ub4FergcUwvbRNi6YWyyMB`

**Recent Commits:**
1. Merge PR #13 - v2 Backend Foundation (folder monitoring)
2. Phase 1 Backend - Automated folder monitoring
3. Frontend build dependencies
4. JPSTAS asset sync
5. Fix storage upload endpoints

**Status:** Clean working tree - ready for new development

