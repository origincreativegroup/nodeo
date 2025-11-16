# nodeo Architecture & Ecosystem Positioning

## Product Ecosystem

nodeo is part of a larger AI-powered workflow ecosystem:

```
┌─────────────────────────────────────────────────────────────┐
│                     Your AI Workflow                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📁 nodeo                → Collects, tags, renames, organizes │
│      ↓                     (Media orchestrator)            │
│                                                             │
│  🧠 AnythingLLM          → Ingests, embeds, retrieves      │
│      ↓                     (Knowledge base)                │
│                                                             │
│  🤖 Ollama               → Generates the final answer      │
│      ↓                     (LLM backend)                   │
│                                                             │
│  🖥️  OpenWebUI           → Your daily cockpit              │
│                           (User interface)                 │
└─────────────────────────────────────────────────────────────┘
```

## nodeo's Core Mission

**Primary Focus:** Media organization and intelligent file management

nodeo should excel at:
1. ✅ **Collecting** - Watch folders, detect new media files
2. ✅ **Tagging** - AI-powered content analysis and metadata extraction
3. ✅ **Renaming** - Intelligent, template-based file renaming
4. ✅ **Organizing** - Project classification and folder structure

**NOT nodeo's job:**
- ❌ Knowledge retrieval (AnythingLLM)
- ❌ Conversational AI (Ollama + OpenWebUI)
- ❌ Document Q&A (AnythingLLM)
- ❌ General-purpose LLM tasks (Ollama)

## Integration Points

### nodeo → AnythingLLM Pipeline

```
1. nodeo processes media:
   - Analyzes images with LLaVA
   - Extracts metadata
   - Generates descriptive filenames
   - Organizes into project folders
   - Creates tags and classifications

2. nodeo exports structured data:
   - JSON manifests with metadata
   - Organized file structure
   - Tag hierarchies
   - Project relationships

3. AnythingLLM ingests:
   - File content
   - nodeo's metadata as context
   - Embeddings for semantic search
   - Cross-references between files

4. Users query via OpenWebUI:
   - "Show me all outdoor portraits from the Smith project"
   - "Find images similar to this one"
   - "What's in this photo?"
```

### Current Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      nodeo Core                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Input Layer:                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • Folder Watcher (watchdog)                      │  │
│  │ • File Upload API                                │  │
│  │ • Batch Import                                   │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                              │
│  Analysis Layer:                                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • LLaVA Vision AI (via Ollama)                   │  │
│  │ • Media Metadata Extractor (ffprobe)             │  │
│  │ • Project Classifier AI                          │  │
│  │ • Tag Extraction                                 │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                              │
│  Organization Layer:                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • Template-Based Renaming (70+ variables)        │  │
│  │ • Project Assignment                             │  │
│  │ • Folder Structure Management                    │  │
│  │ • Tag Hierarchies                                │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                              │
│  Storage Layer:                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • Local Storage (originals/working/exports)      │  │
│  │ • Nextcloud WebDAV                               │  │
│  │ • Cloudflare R2                                  │  │
│  │ • PostgreSQL (metadata)                          │  │
│  └──────────────────────────────────────────────────┘  │
│                         ↓                              │
│  Export Layer:                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │ • JSON Manifests                                 │  │
│  │ • Metadata Export                                │  │
│  │ • API Endpoints                                  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────┘
                         ↓
              ┌──────────────────────┐
              │   AnythingLLM        │
              │   (Knowledge Base)   │
              └──────────────────────┘
```

## Revised Product Positioning

### Updated Tagline
**"Local-first AI media organizer that watches, analyzes, tags, and intelligently renames your files—feeding structured metadata into your knowledge base."**

### Core Value Propositions

1. **Automated Collection** 🔄
   - Watch local folders for new media
   - Real-time detection and queueing
   - Background processing

2. **AI-Powered Tagging** 🏷️
   - Vision AI analysis with LLaVA
   - Automatic tag extraction
   - Scene and object detection
   - Project classification

3. **Intelligent Renaming** ✍️
   - 70+ template variables
   - AI-generated descriptive names
   - Project-aware sequential numbering
   - Preview and rollback

4. **Smart Organization** 📁
   - Deterministic folder structure
   - Project-based grouping
   - Tag hierarchies
   - Metadata manifests

5. **Knowledge Base Ready** 🔗
   - Export structured metadata
   - JSON manifests for ingestion
   - Clean, organized file structure
   - AnythingLLM integration ready

## Data Flow Example

### Scenario: Wedding Photographer Workflow

```
1. Shoot Photos → Import to nodeo watched folder
   ↓

2. nodeo detects files:
   - IMG_0001.jpg
   - IMG_0002.jpg
   - IMG_0003.jpg
   ↓

3. nodeo analyzes with LLaVA:
   - IMG_0001: "bride and groom exchanging rings, indoor, soft lighting"
     Tags: wedding, ceremony, indoor, portrait, couple
   - IMG_0002: "wedding reception dance floor, outdoor, sunset"
     Tags: wedding, reception, outdoor, dance, evening
   - IMG_0003: "wedding cake closeup, indoor, detail shot"
     Tags: wedding, details, food, indoor, closeup
   ↓

4. Project Classifier determines: "Johnson Wedding 2025"
   ↓

5. nodeo renames using template:
   {project_name}_{scene}_{index}_{tags}

   - johnson-wedding-2025_ceremony_001_bride-groom-rings.jpg
   - johnson-wedding-2025_reception_002_dance-floor-sunset.jpg
   - johnson-wedding-2025_details_003_wedding-cake.jpg
   ↓

6. nodeo organizes:
   /storage/working/2025/johnson-wedding/
   ├── ceremony/
   │   └── johnson-wedding-2025_ceremony_001_bride-groom-rings.jpg
   ├── reception/
   │   └── johnson-wedding-2025_reception_002_dance-floor-sunset.jpg
   └── details/
       └── johnson-wedding-2025_details_003_wedding-cake.jpg
   ↓

7. nodeo generates manifest:
   {
     "project": "Johnson Wedding 2025",
     "assets": [
       {
         "file": "johnson-wedding-2025_ceremony_001_bride-groom-rings.jpg",
         "description": "bride and groom exchanging rings, indoor, soft lighting",
         "tags": ["wedding", "ceremony", "indoor", "portrait", "couple"],
         "scene": "ceremony",
         "metadata": {
           "width": 4000,
           "height": 6000,
           "orientation": "portrait"
         }
       },
       ...
     ]
   }
   ↓

8. AnythingLLM ingests:
   - Files from organized structure
   - Metadata from manifest
   - Creates embeddings
   ↓

9. User asks OpenWebUI:
   "Show me all ceremony photos from the Johnson wedding"

   AnythingLLM retrieves using:
   - nodeo's tags (ceremony, wedding)
   - nodeo's project classification (Johnson Wedding 2025)
   - nodeo's folder structure
   - Semantic similarity from embeddings
```

## Focused Feature Set

### ✅ Core Features (Production)
- Image AI analysis with LLaVA
- Automated folder watching
- Template-based batch renaming
- Project classification
- Tag extraction
- Metadata export
- Cloud storage integration

### 🚧 In Progress
- Complete folder watcher processing pipeline
- Automatic rename suggestion generation
- Real-time WebSocket updates

### 🎯 Next Phase (Q1 2025)
- Audio transcription with Whisper
- Video frame analysis
- Cross-media tagging

### 🔮 Future Vision
- Vector embeddings (feed to AnythingLLM)
- Multi-modal correlation
- Advanced search (via AnythingLLM)

## Design Principles

1. **Do One Thing Well** - Focus on media organization, not general AI
2. **Play Nice with Others** - Export clean, structured data for downstream tools
3. **Privacy First** - Local-first processing, optional cloud sync
4. **AI-Powered, Human-Guided** - AI suggests, humans decide
5. **Production Ready** - Reliable, tested, documented

## Technology Stack

### Backend
- **FastAPI** - Modern async Python framework
- **PostgreSQL** - Relational metadata storage
- **Redis** - Background job queue
- **SQLAlchemy** - ORM with async support

### AI/ML
- **LLaVA** - Vision language model (via Ollama)
- **Ollama** - Local AI model serving
- **Whisper** (planned) - Audio transcription

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Tailwind CSS** - Utility-first styling

### Infrastructure
- **Docker Compose** - Container orchestration
- **GitHub Actions** - CI/CD
- **Caddy** - Reverse proxy (optional)

## API Design

### REST Endpoints
```
GET    /api/v2/folders/              # List watched folders
POST   /api/v2/folders/              # Add folder to watch
GET    /api/v2/folders/{id}          # Get folder details
PATCH  /api/v2/folders/{id}          # Update folder settings
DELETE /api/v2/folders/{id}          # Remove folder from watch

GET    /api/v2/suggestions/          # List rename suggestions
POST   /api/v2/suggestions/{id}/accept  # Accept suggestion
POST   /api/v2/suggestions/{id}/reject  # Reject suggestion

GET    /api/projects/                # List projects
GET    /api/projects/{id}/assets     # Get project assets
POST   /api/projects/{id}/export     # Export project manifest

GET    /api/tags/                    # List all tags
GET    /api/tags/{id}/assets         # Get tagged assets
```

### WebSocket
```
WS     /ws/progress                  # Real-time folder processing updates
```

### Export Format (for AnythingLLM)
```json
{
  "schema_version": "1.0",
  "generated_at": "2025-01-16T12:00:00Z",
  "project": {
    "id": "uuid",
    "name": "Johnson Wedding 2025",
    "type": "wedding",
    "created_at": "2025-01-15T10:00:00Z"
  },
  "assets": [
    {
      "id": "uuid",
      "file_path": "/storage/working/2025/johnson-wedding/ceremony/johnson-wedding-2025_ceremony_001.jpg",
      "filename": "johnson-wedding-2025_ceremony_001_bride-groom-rings.jpg",
      "type": "image",
      "ai_analysis": {
        "description": "bride and groom exchanging rings, indoor, soft lighting",
        "tags": ["wedding", "ceremony", "indoor", "portrait", "couple"],
        "scene": "ceremony",
        "objects": ["bride", "groom", "rings", "hands"],
        "mood": "romantic",
        "style": "portrait"
      },
      "technical_metadata": {
        "width": 4000,
        "height": 6000,
        "format": "jpeg",
        "orientation": "portrait",
        "file_size": 3145728,
        "created_at": "2025-01-15T14:30:00Z"
      },
      "project_metadata": {
        "sequence": 1,
        "category": "ceremony",
        "photographer": "John Smith",
        "edited": false
      }
    }
  ],
  "statistics": {
    "total_assets": 350,
    "by_type": {
      "image": 340,
      "video": 10
    },
    "by_category": {
      "ceremony": 120,
      "reception": 180,
      "details": 50
    },
    "ai_analyzed": 350,
    "manually_tagged": 25
  }
}
```

## Success Metrics

### Operational Metrics
- Files processed per hour
- AI analysis accuracy (description relevance)
- Tag quality (manual corrections needed)
- Rename acceptance rate (suggestions accepted)
- Storage efficiency (deduplication ratio)

### User Metrics
- Time saved vs manual organization
- Search precision (after AnythingLLM ingestion)
- User satisfaction with AI-generated names
- Number of projects organized

### Integration Metrics
- Manifest export success rate
- AnythingLLM ingestion compatibility
- API response times
- WebSocket update latency

## Conclusion

nodeo's strength is **media organization**, not knowledge retrieval. By focusing on what it does best—collecting, tagging, renaming, and organizing—nodeo becomes the perfect preprocessor for AnythingLLM, feeding it clean, well-structured, richly-tagged media with comprehensive metadata.

**Core Principle:** nodeo makes your media library organized and searchable. AnythingLLM makes it intelligent and conversational.
