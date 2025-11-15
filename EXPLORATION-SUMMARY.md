# JSPOW Codebase Exploration Summary

Generated: November 15, 2025

## Overview

The jspow codebase has been thoroughly explored and documented. This exploration provides a comprehensive understanding of the project architecture, current file upload mechanisms, asset management systems, and frameworks in use. All findings are documented in three detailed guides for CSV feature implementation.

---

## Key Findings

### 1. Project Architecture
- **Monolithic application** with clean frontend/backend separation
- Frontend: React 18 + TypeScript + Vite + Tailwind CSS
- Backend: FastAPI (Python) + PostgreSQL + Redis
- All running in Docker containers with Docker Compose

### 2. Current Upload System (Proven Pattern)
- **Endpoint:** `POST /api/images/upload` (main.py, lines 307-466)
- **Mechanism:** Multipart form data with FastAPI UploadFile
- **Flow:** File validation → Storage Manager → Database records → Grouping
- **Batch Processing:** Uses UploadBatch + ImageGroup for logical grouping
- **Storage Layout:** `/app/storage/{type}/{year}/{project}/{asset_id}/{filename}`

### 3. Asset Management
- **Core Model:** Image (contains all metadata, AI analysis, storage info)
- **Supporting Models:** UploadBatch, ImageGroup, MediaMetadata, Project
- **Metadata Sidecars:** JSON files stored alongside assets
- **AI Analysis:** LLaVA integration for descriptions, tags, scene detection

### 4. API Endpoints
- **Total Endpoints:** 50+ across main.py and v2 routers
- **Key Categories:** Image management, templates, grouping, projects, storage, rename operations
- **v2 Features:** Folder watching, rename suggestions, activity logging, WebSocket support
- **CSV Support:** Already has CSV export in `/api/v2/activity/export` (activity.py, lines 187-265)

### 5. Framework Details
- **Backend:** FastAPI 0.109.0, SQLAlchemy 2.0.25, asyncpg for async database
- **Storage:** boto3 (R2), webdav4 (Nextcloud), Pillow (image processing)
- **AI:** Ollama 0.1.6 (LLaVA vision model)
- **Frontend:** Axios for HTTP, React Router for navigation, lucide-react for icons
- **All dependencies** documented in requirements.txt and package.json

### 6. CSV/File Processing Capabilities
- **CSV Export:** Fully implemented in activity router (uses Python csv module)
- **Media Metadata:** Comprehensive extraction (dimensions, codec, duration)
- **File Validation:** Extension checking, MIME type detection
- **Batch Operations:** Support for bulk processing with progress tracking
- **Database:** PostgreSQL with Alembic migrations, async operations

---

## Generated Documentation Files

All files located in `/home/user/jspow/` directory:

### 1. CODEBASE-OVERVIEW.md (17 KB, 529 lines)
**Comprehensive reference covering all aspects:**
- Project structure with directory tree
- File upload handling mechanism and flow
- Asset management models and relationships
- Complete API endpoint map (50+ endpoints)
- Framework and library details
- CSV handling capabilities
- Implementation recommendations
- Database schema relationships
- File path reference guide

### 2. CSV-FEATURE-QUICK-REFERENCE.md (13 KB, 371 lines)
**Implementation-focused quick reference:**
- Visual flow diagrams (current upload flow, proposed CSV flow)
- Key files for implementation (backend and frontend)
- Expected CSV format with examples
- Database models to create/extend
- API endpoint design with request/response examples
- Integration checklist
- Testing strategy
- Performance and security considerations

### 3. IMPLEMENTATION-STARTING-POINTS.md (18 KB, 619 lines)
**Code snippets and actionable starting points:**
- Absolute file paths for all critical files
- 5 key code snippets (upload endpoint, CSV export, router pattern, model pattern, API client)
- Step-by-step implementation workflow (5 phases, 12-15 hours estimated)
- Minimal endpoint code to get started
- Environment variables reference
- Useful development commands
- Testing examples
- Architecture diagram

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Total Python files (backend) | 27 files |
| Total React components | 17 components |
| Total API endpoints | 50+ endpoints |
| Database models | 20+ models |
| Lines in main.py | 2,312 |
| Frontend dependencies | 8 packages |
| Backend dependencies | 19 packages |
| Current branch | claude/csv-asset-upload-feature-01Ub4FergcUwvbRNi6YWyyMB |
| Git status | Clean (no uncommitted changes) |

---

## How to Use These Documents

### For Understanding the Codebase
1. Start with **CODEBASE-OVERVIEW.md** for comprehensive architecture
2. Review the project structure and key files sections
3. Understand the upload flow and asset management

### For Implementing CSV Feature
1. Read **CSV-FEATURE-QUICK-REFERENCE.md** for design overview
2. Review the proposed CSV flow diagram
3. Check the database models and API design sections

### For Coding
1. Use **IMPLEMENTATION-STARTING-POINTS.md** as your reference
2. Copy code snippets and adapt to your needs
3. Follow the step-by-step workflow
4. Use the absolute file paths for navigation

---

## Next Steps for CSV Implementation

### Phase 1: Backend Models (2-3 hours)
1. Extend `/home/user/jspow/app/models.py` with:
   - `CSVImportJobStatus` enum
   - `CSVImportJob` model
   - Extended `ActivityActionType` enum
2. Create database migration
3. Apply migration with Alembic

### Phase 2: Backend Service (3-4 hours)
1. Create `/home/user/jspow/app/services/csv_service.py` with:
   - CSV parsing logic
   - Row validation
   - Preview generation
   - Batch import with error handling

### Phase 3: Backend Routes (3-4 hours)
1. Create `/home/user/jspow/app/routers/csv.py` with:
   - Upload & preview endpoint
   - Confirmation endpoint
   - Status tracking endpoint
2. Include router in main.py

### Phase 4: Frontend (3-4 hours)
1. Create CSV import page component
2. Create CSV upload/preview components
3. Extend API client with CSV methods

### Phase 5: Testing & Polish (2-3 hours)
1. Unit tests
2. Integration tests
3. Documentation

**Total Estimated Time:** 12-15 hours of development

---

## Important File Paths to Remember

```
Backend Core
/home/user/jspow/main.py
/home/user/jspow/app/models.py
/home/user/jspow/app/config.py
/home/user/jspow/app/routers/

Frontend Core
/home/user/jspow/frontend/src/services/api.ts
/home/user/jspow/frontend/src/pages/
/home/user/jspow/frontend/src/components/

Configuration
/home/user/jspow/.env.example
/home/user/jspow/requirements.txt
/home/user/jspow/migrations/
```

---

## Key Insights for CSV Implementation

1. **Reuse Patterns:** The existing upload flow (UploadBatch, ImageGroup) can be directly reused for CSV imports
2. **CSV Module:** Python's built-in `csv` module is already imported in activity.py - follow that pattern
3. **Async First:** All database operations must be async (AsyncSession, await)
4. **Storage Manager:** Don't write files directly - use StorageManager from layout.py
5. **Activity Logging:** Extend ActivityLog model to track CSV imports for audit trail
6. **WebSocket Support:** Infrastructure for real-time progress already exists in websocket router
7. **No New Dependencies:** CSV functionality uses only built-in Python modules (csv, io)

---

## Verification Checklist

- [x] Project structure documented
- [x] Upload mechanism fully understood
- [x] Asset models and relationships mapped
- [x] API endpoints cataloged
- [x] Frameworks identified and versions documented
- [x] Existing CSV handling found (activity export)
- [x] Database schema relationships documented
- [x] Implementation path planned with timeline
- [x] Code snippets collected and organized
- [x] Absolute file paths documented

---

## Document Navigation Guide

| If You Want To... | Read This File | Sections |
|---|---|---|
| Understand overall architecture | CODEBASE-OVERVIEW.md | 1-5 |
| Learn about uploads | CODEBASE-OVERVIEW.md | 2 |
| Learn about asset management | CODEBASE-OVERVIEW.md | 3 |
| Design CSV feature | CSV-FEATURE-QUICK-REFERENCE.md | 1-4 |
| See API design | CSV-FEATURE-QUICK-REFERENCE.md | 5-6 |
| Start coding | IMPLEMENTATION-STARTING-POINTS.md | All |
| Get code snippets | IMPLEMENTATION-STARTING-POINTS.md | 2-4 |
| Understand dependencies | CODEBASE-OVERVIEW.md | 5 |
| Plan implementation | CSV-FEATURE-QUICK-REFERENCE.md | 7 |

---

## Support Files in Repository

All documentation files are located in `/home/user/jspow/`:

```
/home/user/jspow/
├── CODEBASE-OVERVIEW.md                    # 529 lines - Architecture overview
├── CSV-FEATURE-QUICK-REFERENCE.md          # 371 lines - Quick reference guide
├── IMPLEMENTATION-STARTING-POINTS.md       # 619 lines - Code snippets & starting points
└── EXPLORATION-SUMMARY.md                  # This file - Summary of exploration
```

---

## Ready to Implement

You now have:
- [x] Complete understanding of the codebase
- [x] Proven patterns to follow
- [x] Code snippets to adapt
- [x] Step-by-step implementation plan
- [x] Absolute file paths for navigation
- [x] Database design recommendations
- [x] API design specifications
- [x] Testing strategy

**The codebase exploration is complete. You are ready to begin CSV feature implementation.**

---

## Questions?

Refer back to the three documentation files:
1. **Architecture questions** → CODEBASE-OVERVIEW.md
2. **Design questions** → CSV-FEATURE-QUICK-REFERENCE.md
3. **Implementation questions** → IMPLEMENTATION-STARTING-POINTS.md

Each document cross-references the others for easy navigation.
