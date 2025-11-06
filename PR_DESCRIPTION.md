## Summary
This PR completes the Nextcloud storage integration by adding automatic synchronization, project-aware asset naming, and comprehensive debugging tools.

**Previous PRs**: Phases 1 and 2 were already merged (Project Management foundation and AI Project Identification)

This PR includes:
- **Phase 3**: Automatic Nextcloud synchronization with project-aware folders
- **Phase 4**: Project-aware asset naming for portfolio optimization
- **Phase 5**: Comprehensive debugging and monitoring infrastructure

---

## Phase 3: Automatic Nextcloud Synchronization ☁️

### New Files
- `app/storage/nextcloud_sync.py` (479 lines) - Nextcloud sync service with project-aware organization

### Features
- **Project-Aware Folder Structure**: `/projects/{project-slug}/originals|exports|metadata`
- **Automatic Sync on Assignment**: Configurable auto-sync when images assigned to projects
- **Manual Sync Operations**: Sync entire projects or specific image batches
- **Sync Status Tracking**: Per-project sync statistics and monitoring
- **Bidirectional Sync Foundation**: Import files from Nextcloud (preview)
- **Connection Validation**: Test Nextcloud connectivity before operations
- **Skip Already-Synced Files**: Efficient sync with force option available
- **Detailed Sync Results**: Success/failure tracking per file

### API Endpoints
- `POST /api/nextcloud/sync/project/{id}` - Sync entire project
- `POST /api/nextcloud/sync/batch` - Sync multiple images
- `GET /api/nextcloud/sync/status/{id}` - Get project sync status
- `GET /api/nextcloud/validate` - Test Nextcloud connection
- `POST /api/nextcloud/import/{id}` - Import files from Nextcloud

### Configuration
- `nextcloud_auto_sync: bool` - Enable/disable automatic sync (default: True)
- `nextcloud_sync_strategy: str` - Sync strategy (default: "mirror")

### Workflow Example
```
1. User assigns images to "ACME Rebrand 2025" project
2. ProjectService updates database (project_id)
3. NextcloudSyncService automatically syncs each image
4. Creates /projects/acme-rebrand-2025/originals/ folder
5. Uploads file with current filename
6. Updates Image.nextcloud_path and storage_type=NEXTCLOUD
7. Returns success or logs warning
```

---

## Phase 4: Project-Aware Asset Naming 📝

### New Files
- `app/services/project_rename.py` (400 lines) - Project-aware rename service

### Features
- **5 New Template Variables**:
  - `{project}` - Project slug (e.g., acme-rebrand-2025)
  - `{project_name}` - Full project name
  - `{client}` - Client name from portfolio metadata
  - `{project_type}` - Project type (client, personal, commercial, etc.)
  - `{project_number}` - Sequential asset number (001, 002, ...)

- **8 Portfolio-Optimized Templates**:
  - `portfolio_client`: `{client}_{project}_{description}_{project_number}`
  - `portfolio_seo`: `{project_name}_{description}`
  - `portfolio_numbered`: `{project}_{project_number}_{description}`
  - `portfolio_dated`: `{project}_{date}_{description}_{project_number}`
  - `portfolio_detailed`: `{client}_{project_type}_{description}_{date}`
  - `portfolio_simple`: `{project}_{description}`
  - `portfolio_professional`: `{client}_{project}_{tags}_{project_number}`
  - `portfolio_web`: `{project_name}_{description}_{tags}`

- **Sequential Numbering**: Automatic per-project asset numbering (prevents duplicates)
- **Preview Before Apply**: See proposed names before committing
- **Batch Rename**: Rename entire projects at once
- **Template Suggestions**: Get recommendations with examples

### API Endpoints
- `GET /api/projects/{id}/rename/suggestions` - Get template suggestions with examples
- `POST /api/projects/{id}/rename/preview` - Preview rename for all project assets
- `POST /api/projects/{id}/rename/apply` - Apply rename to all project assets
- `POST /api/images/{id}/rename/project-aware` - Rename single image with project context

### Example Output
```
Original: IMG_7992.jpg
Renamed:  acme_acme-rebrand-2025_modern-logo_001.jpg

Benefits:
✅ SEO-friendly for portfolio websites
✅ Professional client-ready naming
✅ Sequential numbering prevents duplicates
✅ Client name for easy attribution
```

---

## Phase 5: Debugging and Monitoring Infrastructure 🔍

### New Files
- `app/debug_utils.py` (331 lines) - Comprehensive debugging utilities

### Features

#### DebugInfo Class
- `get_system_info()` - CPU, memory, disk usage via psutil
- `get_environment_info()` - App configuration and settings
- `check_database_connection()` - Database connectivity with response timing
- `check_ollama_connection()` - LLaVA/Ollama AI service connectivity
- `check_nextcloud_connection()` - Cloud storage connectivity
- `get_storage_info()` - File counts in storage directories
- `get_database_stats()` - Images, projects, groups, storage type statistics

#### RequestLogger Class
- HTTP request/response logging with timing
- Automatic error logging with stack traces
- Performance monitoring for every endpoint

#### Enhanced Logging
- Multi-handler logging (console + file + error log)
- Structured logging with timestamps and context
- Separate error log for quick issue identification

### API Endpoints
- `GET /debug/system` - System, environment, storage, and database stats
- `GET /debug/health-full` - Full health check with all service connections
- `GET /debug/logs/recent?lines=50` - Recent log entries
- `GET /debug/errors/recent?lines=50` - Recent error log entries

### Request/Response Logging Middleware
- Logs all HTTP requests with method, path, status code, duration
- Automatic error capture and logging
- Performance monitoring for bottleneck identification

### Dependencies
- Added `psutil 5.9.8` for system monitoring

---

## Test Plan

### Phase 3 - Nextcloud Sync
- [ ] Create a project with name and client metadata
- [ ] Assign images to the project
- [ ] Verify images are synced to Nextcloud at `/projects/{slug}/originals/`
- [ ] Check sync status: `GET /api/nextcloud/sync/status/{id}`
- [ ] Verify `Image.nextcloud_path` is updated
- [ ] Test manual sync: `POST /api/nextcloud/sync/project/{id}`
- [ ] Test force re-sync with `force=true`
- [ ] Verify connection: `GET /api/nextcloud/validate`

### Phase 4 - Project Naming
- [ ] Get template suggestions: `GET /api/projects/{id}/rename/suggestions`
- [ ] Preview rename: `POST /api/projects/{id}/rename/preview`
- [ ] Apply rename: `POST /api/projects/{id}/rename/apply`
- [ ] Verify sequential numbering (001, 002, 003...)
- [ ] Check filenames include project context (client, project name)
- [ ] Test single image rename: `POST /api/images/{id}/rename/project-aware`

### Phase 5 - Debug Tools
- [ ] Check system info: `GET /debug/system`
- [ ] Run full health check: `GET /debug/health-full`
- [ ] Verify all services (database, Ollama, Nextcloud) are reported correctly
- [ ] Check recent logs: `GET /debug/logs/recent`
- [ ] Check error logs: `GET /debug/errors/recent`
- [ ] Verify request logging middleware is working (check logs)
- [ ] Verify log files created at `logs/jspow.log` and `logs/errors.log`

---

## Files Changed

**Phase 3 (4 files, +654 lines)**
- `app/storage/nextcloud_sync.py` (new, 479 lines)
- `app/services/project_service.py` (modified)
- `app/config.py` (modified)
- `main.py` (+149 lines)

**Phase 4 (3 files, +547 lines)**
- `app/services/project_rename.py` (new, 400 lines)
- `app/services/template_parser.py` (modified)
- `main.py` (+102 lines)

**Phase 5 (3 files, +443 lines)**
- `app/debug_utils.py` (new, 331 lines)
- `main.py` (modified)
- `requirements.txt` (modified)

**Total: 10 files changed, 1,644 insertions(+)**

---

## Benefits

### For Graphic Designers
✅ **Automatic Cloud Backup**: All portfolio assets safely stored in Nextcloud
✅ **Professional Naming**: SEO-friendly, client-ready filenames
✅ **Project Organization**: Assets grouped by client/project in cloud
✅ **Sequential Numbering**: No duplicate filenames within projects
✅ **Portfolio Ready**: Export-ready naming for portfolio websites

### For Developers
✅ **Comprehensive Monitoring**: Real-time system and service health
✅ **Request Logging**: Track performance and debug issues
✅ **Error Tracking**: Separate error log for quick issue identification
✅ **Service Health Checks**: Validate database, AI, and storage connectivity
