# CSV Feature Implementation - Starting Points & Code Snippets

## Absolute File Paths (Use These for Navigation)

### Backend Critical Files

```
/home/user/jspow/main.py                          # Main app entry (2312 lines)
/home/user/jspow/app/models.py                    # Database models
/home/user/jspow/app/config.py                    # Configuration/settings
/home/user/jspow/app/database.py                  # Database setup
/home/user/jspow/app/routers/activity.py          # CSV export reference (lines 187-265)
/home/user/jspow/app/routers/folders.py           # Router pattern reference
/home/user/jspow/app/routers/suggestions.py       # Router pattern reference
/home/user/jspow/app/storage/layout.py            # Storage manager (abstract away file ops)
/home/user/jspow/app/services/project_service.py  # Asset relationship example
/home/user/jspow/requirements.txt                 # Python dependencies
```

### Frontend Critical Files

```
/home/user/jspow/frontend/src/services/api.ts     # API client (Axios patterns)
/home/user/jspow/frontend/src/context/AppContext.tsx  # Global state
/home/user/jspow/frontend/src/pages/RenameManager.tsx  # Main layout reference
/home/user/jspow/frontend/src/pages/Dashboard.tsx      # Alternative layout
/home/user/jspow/frontend/package.json            # Frontend dependencies
```

### Configuration Files

```
/home/user/jspow/.env.example                     # Environment template
/home/user/jspow/docker-compose.yml               # Container setup
/home/user/jspow/alembic.ini                      # Database migration config
```

---

## Key Code Snippets to Reference

### 1. Upload Endpoint Pattern (What you're building on)

**File:** `/home/user/jspow/main.py` (lines 307-466)

```python
@app.post("/api/images/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """Upload and analyze images"""
    
    if len(files) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_batch_size} files allowed"
        )

    # KEY: Create UploadBatch to group uploads
    upload_batch = UploadBatch(
        label=datetime.utcnow().strftime("Upload %Y-%m-%d %H:%M"),
        source="web",
        attributes={"total_expected": len(files)},
    )
    db.add(upload_batch)
    await db.flush()

    # KEY: Create ImageGroup for batch grouping
    upload_group = ImageGroup(
        name=upload_label,
        group_type=GroupType.UPLOAD_BATCH,
        attributes={
            "cluster_key": f"upload:{upload_batch.id}",
            "total_expected": len(files),
            "image_count": 0,
        },
        upload_batch_id=upload_batch.id,
    )
    db.add(upload_group)
    
    # KEY: For each file, follow this pattern:
    for file in files:
        try:
            # 1. Validate extension
            ext = Path(file.filename).suffix.lower().lstrip('.')
            is_image = ext in settings.allowed_image_exts
            is_video = ext in settings.allowed_video_exts
            if not (is_image or is_video):
                # Error handling
                continue

            # 2. Save files using StorageManager
            content = await file.read()
            uploaded_at = datetime.utcnow()
            asset_id = uuid4().hex
            project_code = settings.default_project_code

            original_path = storage_manager.write_file(
                "originals",
                asset_id,
                file.filename,
                content,
                created_at=uploaded_at,
                project=project_code,
            )
            working_path = storage_manager.write_file(
                "working",
                asset_id,
                file.filename,
                content,
                created_at=uploaded_at,
                project=project_code,
            )

            # 3. Write metadata sidecar
            storage_manager.write_metadata(
                asset_id,
                {
                    "asset_id": asset_id,
                    "project": project_code,
                    "original_path": str(original_path),
                    "working_path": str(working_path),
                    "uploaded_at": uploaded_at.isoformat(),
                    "published": False,
                },
                created_at=uploaded_at,
                project=project_code,
            )

            # 4. Create Image record
            metadata_result = await metadata_service.get_metadata(
                working_path, 
                mime_type=file.content_type
            )
            image_record = Image(
                original_filename=file.filename,
                current_filename=file.filename,
                file_path=str(working_path),
                file_size=len(content),
                mime_type=file.content_type,
                media_type=MediaType.IMAGE,
                width=metadata_result.width,
                height=metadata_result.height,
                storage_type=StorageType.LOCAL,
                upload_batch_id=upload_batch.id,
            )
            db.add(image_record)
            await db.flush()

            # 5. Link to group
            db.add(
                ImageGroupAssociation(
                    group_id=upload_group.id,
                    image_id=image_record.id,
                )
            )

        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    await db.commit()
    return {
        "total": len(files),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results,
        "upload_batch_id": upload_batch.id,
        "group_id": upload_group.id,
    }
```

### 2. CSV Export Pattern (What Already Exists)

**File:** `/home/user/jspow/app/routers/activity.py` (lines 187-265)

```python
import csv
import io

@router.get("/export")
async def export_activity_log(
    format: str = "csv",
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Export activity log as CSV or JSON"""
    
    since_date = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.created_at >= since_date)
        .order_by(ActivityLog.created_at.desc())
    )
    logs = result.scalars().all()

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow([
            "ID",
            "Action Type",
            "Status",
            "Original Filename",
            "New Filename",
            "Folder Path",
            "Error Message",
            "Created At"
        ])
        
        # Write data
        for log in logs:
            writer.writerow([
                str(log.id),
                log.action_type.value,
                log.status,
                log.original_filename or "",
                log.new_filename or "",
                log.folder_path or "",
                log.error_message or "",
                log.created_at.isoformat()
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=activity_log_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )
```

### 3. Router Pattern (Template to Follow)

**File:** `/home/user/jspow/app/routers/activity.py` (lines 1-30)

```python
"""API endpoints for activity log (JSPOW v2)"""
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    ActivityLog,
    ActivityActionType,
    WatchedFolder
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/csv", tags=["CSV"])

# Request/Response Models
class CSVImportRequest(BaseModel):
    filename: str
    preview: bool = True

# Endpoints
@router.post("", response_model=dict)
async def upload_csv(
    # parameters
    db: AsyncSession = Depends(get_db)
):
    """Upload CSV file"""
    pass
```

### 4. Database Model Pattern

**File:** `/home/user/jspow/app/models.py` (lines 408-427)

```python
from sqlalchemy import Column, String, Integer, DateTime, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum

class ActivityLog(Base):
    """Activity log for all operations"""
    __tablename__ = "activity_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    watched_folder_id = Column(UUID(as_uuid=True), ForeignKey("watched_folders.id", ondelete="SET NULL"))
    asset_id = Column(Integer, ForeignKey("images.id", ondelete="SET NULL"))
    action_type = Column(SQLEnum(ActivityActionType), nullable=False)
    original_filename = Column(String(500))
    new_filename = Column(String(500))
    folder_path = Column(Text)
    status = Column(String(50), nullable=False)  # success, failure
    error_message = Column(Text)
    metadata = Column(JSON)  # additional context
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    watched_folder = relationship("WatchedFolder", back_populates="activity_logs")
    asset = relationship("Image", back_populates="activity_logs")
```

### 5. API Client Pattern (Frontend)

**File:** `/home/user/jspow/frontend/src/services/api.ts` (lines 84-97)

```typescript
export const uploadImages = async (files: FileList): Promise<UploadResponse> => {
  const formData = new FormData()
  Array.from(files).forEach((file) => {
    formData.append('files', file)
  })

  const response = await api.post<UploadResponse>('/images/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}
```

---

## Implementation Workflow

### Step 1: Backend Models (2-3 hours)

1. **Extend `/home/user/jspow/app/models.py`:**
   - Add `CSVImportJobStatus` enum
   - Add `CSVImportJob` model class
   - Extend `ActivityActionType` enum with CSV actions
   - Create migration

2. **Create migration:**
   ```bash
   cd /home/user/jspow
   alembic revision --autogenerate -m "Add CSV import job model"
   alembic upgrade head
   ```

### Step 2: Backend Service (3-4 hours)

1. **Create `/home/user/jspow/app/services/csv_service.py`:**
   - CSV parsing logic (use Python csv module)
   - Row validation
   - Preview generation
   - Batch import with error handling
   - Progress tracking

2. **Add CSV-specific imports to `/home/user/jspow/requirements.txt`:**
   - Already have csv (built-in)
   - May need pandas if doing complex operations (optional)

### Step 3: Backend Routes (3-4 hours)

1. **Create `/home/user/jspow/app/routers/csv.py`:**
   - `POST /api/csv/import` - Upload & preview
   - `POST /api/csv/import/{job_id}/confirm` - Start import
   - `GET /api/csv/import/{job_id}` - Get status
   - `GET /api/csv/import` - List jobs

2. **Include in `/home/user/jspow/main.py`:**
   ```python
   from app.routers import csv
   app.include_router(csv.router)
   ```

### Step 4: Frontend Components (3-4 hours)

1. **Create CSV upload UI:**
   - File input component
   - Preview table component
   - Progress tracker component
   - Result summary component

2. **Update API client:**
   - Add CSV methods to `/home/user/jspow/frontend/src/services/api.ts`

3. **Create CSV import page:**
   - `/home/user/jspow/frontend/src/pages/CSVImportPage.tsx`

### Step 5: Testing & Polish (2-3 hours)

1. Backend tests
2. Frontend tests
3. Integration tests
4. Documentation

---

## Quick Start for First Endpoint

### Create minimal `/home/user/jspow/app/routers/csv.py`:

```python
"""CSV import endpoints"""
import logging
import csv
import io
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import UploadBatch, ImageGroup, GroupType, ActivityLog, ActivityActionType
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/csv", tags=["CSV Import"])

class CSVImportResponse(BaseModel):
    job_id: int
    filename: str
    total_rows: int
    preview_rows: List[dict]
    validation_summary: dict

@router.post("/import", response_model=CSVImportResponse)
async def import_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload CSV and return preview"""
    
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    # Read CSV content
    content = await file.read()
    csv_text = content.decode('utf-8')
    
    # Parse CSV
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(csv_reader)
    
    # Create UploadBatch for CSV import
    upload_batch = UploadBatch(
        label=f"CSV Import {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        source="csv_import",
        attributes={"total_expected": len(rows), "filename": file.filename}
    )
    db.add(upload_batch)
    await db.flush()
    
    # TODO: Add validation logic
    
    return {
        "job_id": upload_batch.id,
        "filename": file.filename,
        "total_rows": len(rows),
        "preview_rows": rows[:5],  # First 5 rows
        "validation_summary": {
            "total": len(rows),
            "valid": len(rows),
            "invalid": 0,
            "errors": []
        }
    }
```

### Update `/home/user/jspow/main.py` (around line 155):

```python
from app.routers import folders, suggestions, activity, websocket, csv
app.include_router(folders.router)
app.include_router(suggestions.router)
app.include_router(activity.router)
app.include_router(websocket.router)
app.include_router(csv.router)  # ADD THIS
```

---

## Environment Variables to Know

**From `/home/user/jspow/.env.example` and `/home/user/jspow/app/config.py`:**

```env
# File limits
MAX_UPLOAD_SIZE_MB=100
ALLOWED_IMAGE_EXTENSIONS=jpg,jpeg,png,gif,webp,bmp,tiff
ALLOWED_VIDEO_EXTENSIONS=mp4,mov,avi,mkv,webm
MAX_BATCH_SIZE=50

# Storage
STORAGE_ROOT=/app/storage
DEFAULT_PROJECT_CODE=general

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/jspow

# Redis
REDIS_URL=redis://redis:6379/0
```

---

## Useful Commands

```bash
# Start development server
cd /home/user/jspow
docker-compose up -d

# Run migrations
alembic upgrade head

# Access logs
docker-compose logs -f app

# Test CSV parsing locally
python -c "
import csv
import io
with open('test.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(row)
"

# View database
docker-compose exec postgres psql -U postgres -d jspow

# Frontend dev
cd frontend
npm run dev
```

---

## Testing Your CSV Feature

### Test File Creation

Create `/home/user/jspow/test_assets.csv`:
```csv
filename,project,tags,description
photo1.jpg,travel,"sunset,landscape",Beautiful mountain landscape
photo2.jpg,portfolio,"portrait,professional",LinkedIn headshot
```

### Frontend Test

```typescript
// In browser console
const formData = new FormData()
const csvFile = new File(
  ['filename,project,tags\ntest.jpg,general,test'],
  'test.csv',
  { type: 'text/csv' }
)
formData.append('file', csvFile)

fetch('/api/csv/import', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(d => console.log(d))
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│     Frontend (React/TypeScript)         │
├─────────────────────────────────────────┤
│ CSVImportPage → CSV Upload Component    │
│    ↓ Upload CSV                         │
│    ↓ GET preview                        │
│    ↓ Show preview table                 │
│    ↓ Confirm import                     │
│    ↓ Track progress via WS              │
└─────────────────────────────────────────┘
            ↓ HTTP/WebSocket
┌─────────────────────────────────────────┐
│     Backend (FastAPI/Python)            │
├─────────────────────────────────────────┤
│ app/routers/csv.py (NEW)                │
│   POST /api/csv/import                  │
│   POST /api/csv/import/{id}/confirm     │
│                ↓                        │
│ app/services/csv_service.py (NEW)       │
│   - Parse CSV                           │
│   - Validate rows                       │
│   - Generate preview                    │
│   - Execute import                      │
│                ↓                        │
│ app/models.py (EXTEND)                  │
│   CSVImportJob (NEW)                    │
│   ActivityActionType (EXTEND)           │
│                ↓                        │
│ Database (PostgreSQL)                   │
│   - csv_import_jobs table               │
│   - activity_log updates                │
└─────────────────────────────────────────┘
```
