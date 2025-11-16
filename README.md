# nodeo

**Local-first AI media orchestrator for intelligent renaming, tagging, and transcription across images, audio, and video.**

> **Formerly jspow** - This project has been renamed and repositioned to reflect its evolution from an image-focused tool to a comprehensive multi-modal media organization engine.

## Overview

nodeo is designed to grow from an intelligent image renamer into a full multi-modal media organization engine. It watches your local folders and libraries, analyzes content using AI, and suggests intelligent file renames, tags, and categories across multiple media types.

### Current Capabilities

- **Images**: AI-powered description, tagging, and scene detection using LLaVA vision model
- **Audio** (early support): Speech-to-text, transcription, and basic tagging
- **Video** (early support): Transcription, scene/segment naming, and tagging
- **Automated Folder Monitoring**: Watch directories for new files and process automatically
- **Batch Renaming**: Custom naming templates with AI-generated variables
- **Cloud Integration**: Nextcloud WebDAV, Cloudflare R2, and Cloudflare Stream support

### Future Direction

nodeo is evolving into a comprehensive multi-modal orchestrator that handles:
- Advanced audio analysis and music tagging
- Video scene segmentation and intelligent chapter marking
- Cross-media correlation and organization
- Advanced metadata extraction and management

## Features

- **AI-Powered Analysis**: Automatic content description, tagging, and scene detection using LLaVA via Ollama
- **Folder Monitoring (v2)**: Real-time watch and analysis of local directories
- **Batch Renaming**: Custom naming templates with variables like `{description}`, `{tags}`, `{date}`, `{index}`
- **Preview Mode**: See proposed names before applying changes
- **Storage Integration**:
  - Nextcloud WebDAV for asset management
  - Cloudflare R2 for cloud storage
  - Cloudflare Stream for video hosting
- **Web Interface**: Modern React-based UI with real-time progress tracking
- **Docker Deployment**: Fully containerized with Docker Compose

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Database for media metadata
- **Redis** - Queue for background processing
- **Ollama** - Local AI model serving (LLaVA vision model)
- **SQLAlchemy** - Async ORM

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling

### Infrastructure
- **Docker & Docker Compose** - Containerization
- **Caddy** - Reverse proxy (on pi-net)
- **GitHub Actions** - CI/CD automation
- **Self-hosted runner** - On pi-forge

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama running with LLaVA model installed
- (Optional) Nextcloud instance
- (Optional) Cloudflare R2 and Stream accounts

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/nodeo.git
   cd nodeo
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start services**
   ```bash
   docker compose up -d
   ```

4. **Access the application**
   - Local: http://localhost:8002
   - LAN (with pi-net proxy): https://nodeo.lan

## Configuration

See \`.env.example\` for all available options. Key settings:

\`\`\`env
# Ollama (required)
OLLAMA_HOST=http://192.168.50.248:11434
OLLAMA_MODEL=llava

# Nextcloud (optional)
NEXTCLOUD_URL=https://nextcloud.lan
NEXTCLOUD_USERNAME=your-username
NEXTCLOUD_PASSWORD=your-password

# Storage layout
STORAGE_ROOT=/app/storage
DEFAULT_PROJECT_CODE=general

# Feature flags (disabled by default)
ENABLE_MANIFEST_GENERATION=false
ENABLE_CLOUDFLARE_R2=false
ENABLE_CLOUDFLARE_STREAM=false

# Cloudflare (optional)
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_API_TOKEN=
CLOUDFLARE_R2_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_ACCESS_KEY=
CLOUDFLARE_R2_BUCKET=nodeo-images
CLOUDFLARE_R2_ENDPOINT=
CLOUDFLARE_R2_ORIGINALS_PATH=originals/
CLOUDFLARE_R2_WORKING_PATH=working/
CLOUDFLARE_R2_EXPORTS_PATH=exports/
CLOUDFLARE_R2_METADATA_PATH=metadata/
CLOUDFLARE_STREAM_ACCOUNT_ID=
CLOUDFLARE_STREAM_API_TOKEN=
\`\`\`

## Storage Layout

Uploaded assets are organized under \`STORAGE_ROOT\` using a deterministic structure to separate working files from immutable originals:

\`\`\`
/app/storage/{type}/{year}/{project}/{asset_id}/
\`\`\`

- \`type\` — one of \`originals\`, \`working\`, \`exports\`, or \`metadata\`
- \`year\` — the four digit year the asset was ingested
- \`project\` — slug generated from \`DEFAULT_PROJECT_CODE\` (or a supplied project label)
- \`asset_id\` — unique identifier per upload (UUID)

Original uploads are preserved in the \`originals\` tree, while the \`working\` tree contains the files referenced by the database and rename workflows. Metadata JSON blobs are stored alongside each asset under the \`metadata\` tree, enabling synchronization tooling to capture publication status and historical context.

## Manifests and Sync Preparation

Each \`{type}/{year}/{project}\` folder can generate a \`manifest.json\` containing file hashes, stored metadata, and a \`published\` flag for every asset directory. This supports eventual synchronization with Cloudflare or other remote targets. To generate a manifest, run a short Python snippet (for example from \`poetry run python\` or the FastAPI shell):

\`\`\`python
from app.storage import storage_manager

# Generate manifest for the current year's working copies
storage_manager.generate_manifest("working", 2024, "general")
\`\`\`

Manifests live inside the corresponding folder (e.g., \`/app/storage/working/2024/general/manifest.json\`) and can be consumed by future sync tooling to detect drift between local and remote copies.

## Usage

### Naming Templates

Available variables:
- \`{description}\` - AI-generated description
- \`{tags}\` - Top AI tags
- \`{scene}\` - Scene type
- \`{date}\` - Current date
- \`{index}\` - Sequential index

**Example:** \`{description}_{date}_{index}\` → \`blue_sky_sunset_20250105_001\`

## Deployment

This project uses GitHub Actions for automatic deployment to pi-forge. Push to main branch to trigger deployment.

Access at: https://nodeo.lan (LAN only)

## Migration from jspow

If you're upgrading from the previous jspow installation:

1. **Database**: Update your \`DATABASE_URL\` from \`jspow\` to \`nodeo\` in your environment configuration.
2. **Storage paths**: Your existing storage will continue to work. Consider updating Nextcloud paths from \`/jspow\` to \`/nodeo\`.
3. **Container names**: Docker containers are now named \`nodeo-app\`, \`nodeo-postgres\`, \`nodeo-redis\` instead of \`jspow-*\`.
4. **Configuration**: Review your \`.env\` file and update any references to \`jspow\` to \`nodeo\`.

## License

MIT License
