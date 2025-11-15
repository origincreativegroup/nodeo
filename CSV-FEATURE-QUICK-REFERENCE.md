# CSV Upload Feature - Quick Reference Guide

## Current Upload Flow (as reference for CSV implementation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          JSPOW FILE UPLOAD FLOW                              │
└─────────────────────────────────────────────────────────────────────────────┘

FRONTEND
────────────────────────────────────────────────────────────────────────────────
  [File Input] → [Upload Files] → [FormData with multiple files]
                        ↓
                   API Call
                   (axios)
                        ↓
POST /api/images/upload

BACKEND
────────────────────────────────────────────────────────────────────────────────
  [FastAPI Endpoint] → [Validation]
       ↓                 ↓
    Receive            Check extensions
   UploadFile         (allowed_image_exts,
   files list         allowed_video_exts)
       ↓
  [Create Database Records]
  ├─ UploadBatch (grouping label, source="web")
  ├─ ImageGroup (group_type=UPLOAD_BATCH)
  └─ ImageGroupAssociation (link batch to group)
       ↓
  [For Each File]
  ├─ Generate UUID asset_id
  ├─ Read file content
  ├─ Extract metadata (dimensions, codec, etc.)
  ├─ [Storage Manager]
  │  ├─ Write original: /storage/originals/{year}/{project}/{asset_id}/{filename}
  │  ├─ Write working: /storage/working/{year}/{project}/{asset_id}/{filename}
  │  └─ Write metadata: /storage/metadata/{year}/{project}/{asset_id}/metadata.json
  ├─ Create Image record (links to MediaMetadata, UploadBatch)
  └─ Create ImageGroupAssociation
       ↓
  [Return Results]
  {
    "total": 5,
    "succeeded": 4,
    "results": [
      {"filename": "photo1.jpg", "success": true, "id": 123},
      {"filename": "photo2.jpg", "success": true, "id": 124},
      ...
    ],
    "upload_batch_id": 42,
    "group_id": 99
  }
```

---

## CSV Import Flow (PROPOSED for new feature)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CSV IMPORT FEATURE FLOW                               │
└─────────────────────────────────────────────────────────────────────────────┘

FRONTEND
────────────────────────────────────────────────────────────────────────────────
  [CSV File Input] → [Preview] → [Confirm Import] → [Progress Tracking]
         ↓               ↓             ↓                  ↓
    Parse CSV      Show table    Send confirmation   WebSocket
    (headers,       with data     to backend         updates
     rows)          validation

API CALLS:
  1. POST /api/csv/import (upload CSV file)
     → Returns preview with row count, validation errors
     
  2. POST /api/csv/import/{job_id}/confirm
     → Starts actual import process
     
  3. WS /api/v2/ws/progress (optional)
     → Real-time progress updates

BACKEND
────────────────────────────────────────────────────────────────────────────────
  [CSV Parsing]
  ├─ Validate CSV format
  ├─ Extract headers
  ├─ Validate required columns (filename, project?, tags?)
  └─ Generate row previews
  
       ↓
  [Create CSVImportJob]
  ├─ Store CSV metadata
  ├─ Store row count
  ├─ Status: PENDING
  └─ Generate preview data
  
       ↓
  [On Confirmation]
  ├─ Create UploadBatch (source="csv_import")
  ├─ Create ImageGroup (group_type=CSV_IMPORT_BATCH)
  └─ Update CSVImportJob status: PROCESSING
  
       ↓
  [For Each Row]
  ├─ Find or reference asset by criteria (filename, asset_id, etc.)
  ├─ Extract metadata (tags, description, project, etc.)
  ├─ Update Image record with metadata
  ├─ Create/update metadata sidecar
  ├─ Log activity (ActivityLog action_type=CSV_IMPORT)
  └─ Track progress
  
       ↓
  [Completion]
  ├─ CSVImportJob status: COMPLETED
  ├─ Return summary:
  │  {
  │    "total_rows": 100,
  │    "successful": 98,
  │    "failed": 2,
  │    "errors": [
  │      {"row": 5, "error": "File not found"},
  │      ...
  │    ]
  │  }
  └─ Broadcast completion via WebSocket
```

---

## Key Files for Implementation

### Backend Files to Modify/Create

| File | Purpose | Action |
|------|---------|--------|
| `/app/models.py` | Add CSVImportJob, extend ActivityActionType | Extend |
| `/app/routers/` | NEW: Create `csv.py` router | Create |
| `/app/services/` | NEW: Create `csv_service.py` | Create |
| `/main.py` | Include CSV router, maybe move route | Modify |
| `migrations/` | Create migration for CSVImportJob | Create |

### Frontend Files to Modify/Create

| File | Purpose | Action |
|------|---------|--------|
| `/frontend/src/pages/` | NEW: CSVImportPage.tsx | Create |
| `/frontend/src/services/api.ts` | Add CSV API methods | Extend |
| `/frontend/src/components/` | CSV upload/preview components | Create |

---

## CSV Expected Format Example

```csv
filename,project,tags,description,title,alt_text
landscape-001.jpg,travel,"sunset,mountain,nature",A beautiful sunset over the mountains,Mountain Sunset,Golden sunset with mountains in background
portrait-002.jpg,portfolio,"portrait,headshot,professional",Professional headshot for LinkedIn,Professional Portrait,Corporate headshot on neutral background
abstract-003.png,experimental,"abstract,digital,art",Digital abstract composition,Abstract Design,Colorful abstract digital artwork
```

**Column Mapping:**
- `filename`: References existing file or source file to locate
- `project`: Project name (will create/assign to project)
- `tags`: Comma-separated list of tags (split and create AssetTag records)
- `description`: AI description field (ai_description)
- `title`: Asset metadata title
- `alt_text`: Accessibility text

**Other Possible Columns:**
- `asset_id`: Reference existing Image record
- `scene`: Scene type (indoor, outdoor, etc.)
- `file_path`: Full path to locate file on disk
- `group_name`: Assign to specific ImageGroup

---

## Database Models to Create/Extend

### New Model: CSVImportJob

```python
class CSVImportJobStatus(str, Enum):
    PENDING = "pending"           # Uploaded, preview ready
    PROCESSING = "processing"     # Import in progress
    COMPLETED = "completed"       # Finished successfully
    FAILED = "failed"            # Failed with errors

class CSVImportJob(Base):
    __tablename__ = "csv_import_jobs"
    
    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    status = Column(SQLEnum(CSVImportJobStatus), default=CSVImportJobStatus.PENDING)
    
    # CSV Metadata
    total_rows = Column(Integer)
    successful_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    
    # Storage
    csv_file_path = Column(String(1000))  # Store uploaded CSV
    preview_data = Column(JSON)           # First N rows for preview
    validation_errors = Column(JSON)      # Row-level errors
    import_results = Column(JSON)         # Final results
    
    # Links
    upload_batch_id = Column(Integer, ForeignKey("upload_batches.id"))
    group_id = Column(Integer, ForeignKey("image_groups.id"))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
```

### Extended Models

**ActivityActionType (enum extension)**
```python
class ActivityActionType(str, Enum):
    # ... existing values ...
    CSV_IMPORT = "csv_import"
    CSV_SEARCH = "csv_search"
    METADATA_UPDATE = "metadata_update"
```

---

## API Endpoint Design

### CSV Import Endpoints

```
POST   /api/csv/import              - Upload CSV, return preview
POST   /api/csv/import/{job_id}/confirm  - Confirm & start import
GET    /api/csv/import/{job_id}     - Get import status
GET    /api/csv/import/{job_id}/progress - Get progress (alternative to WS)
GET    /api/csv/import              - List all import jobs

POST   /api/csv/search              - Search assets by CSV criteria
```

### Request/Response Examples

**POST /api/csv/import** (Upload & Preview)
```json
Request: FormData with CSV file

Response 200:
{
  "job_id": "12345",
  "filename": "assets.csv",
  "total_rows": 100,
  "preview_rows": [
    {"row": 1, "filename": "photo1.jpg", "project": "travel", "valid": true},
    {"row": 2, "filename": "photo2.jpg", "project": "portfolio", "valid": true},
    {"row": 5, "filename": "missing.jpg", "project": "test", "valid": false, "error": "File not found"}
  ],
  "validation_summary": {
    "total": 100,
    "valid": 98,
    "invalid": 2,
    "errors": [
      {"row": 5, "error": "File not found"},
      {"row": 12, "error": "Unknown project"}
    ]
  }
}
```

**POST /api/csv/import/{job_id}/confirm**
```json
Response 202 Accepted:
{
  "job_id": "12345",
  "status": "processing",
  "message": "Import started, track progress via WebSocket"
}
```

**WebSocket /api/v2/ws/progress** (Optional for real-time updates)
```json
{
  "type": "csv_import_progress",
  "job_id": "12345",
  "processed": 45,
  "total": 100,
  "percentage": 45,
  "current_file": "photo45.jpg",
  "status": "processing"
}
```

---

## Integration Checklist

- [ ] **Models:** Add CSVImportJob model, extend enums
- [ ] **Database:** Create migration for new table
- [ ] **Backend Services:** Create csv_service.py with parsing logic
- [ ] **Backend Routes:** Create csv.py router with endpoints
- [ ] **Frontend Pages:** Create CSVImportPage component
- [ ] **Frontend Components:** Create CSV upload/preview components
- [ ] **API Client:** Extend api.ts with CSV methods
- [ ] **Testing:** Unit tests for CSV parsing
- [ ] **Documentation:** Update README with CSV feature docs

---

## Testing Strategy

### CSV Parsing Tests
- Valid CSV with all columns
- CSV with missing optional columns
- CSV with invalid data (file not found, unknown project)
- CSV with special characters in filenames
- Large CSV (1000+ rows)

### Integration Tests
- Upload CSV → Get preview → Confirm import → Check results
- Verify metadata is correctly assigned
- Verify activity logs are created
- Verify upload batch/group are created

### Frontend Tests
- CSV file input validation
- Preview table rendering
- Progress tracking
- Error display

---

## Performance Considerations

1. **CSV Parsing:**
   - Use streaming for large files (1000+ rows)
   - Validate rows in batches

2. **Database Operations:**
   - Batch insert Image records
   - Use bulk_insert_mappings for efficiency
   - Consider transaction boundaries

3. **Progress Tracking:**
   - Update every N rows (e.g., every 10 rows)
   - Broadcast via WebSocket without overwhelming client

4. **File Handling:**
   - Stream CSV file instead of loading entire file in memory
   - Don't duplicate assets unnecessarily

---

## Security Considerations

1. **CSV Injection Prevention:**
   - Sanitize CSV content
   - Don't directly execute formulas from CSV

2. **File Access:**
   - Validate file paths to prevent directory traversal
   - Restrict to configured storage directories only

3. **Project Assignment:**
   - Verify user has permission to assign to projects
   - Log all assignments for audit trail

4. **Data Validation:**
   - Validate all CSV data before database insert
   - Implement rate limiting on CSV import endpoint
