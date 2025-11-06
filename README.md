# jspow

AI-powered image file renaming and organization tool using LLaVA vision model.

## Features

- **AI Image Analysis**: Automatic image description, tagging, and scene detection using LLaVA via Ollama
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
- **PostgreSQL** - Database for image metadata
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
   git clone https://github.com/yourusername/jspow.git
   cd jspow
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
   - LAN (with pi-net proxy): https://jspow.lan

## Configuration

See `.env.example` for all available options. Key settings:

```env
# Ollama (required)
OLLAMA_HOST=http://192.168.50.248:11434
OLLAMA_MODEL=llava

# Nextcloud (optional)
NEXTCLOUD_URL=https://nextcloud.lan
NEXTCLOUD_USERNAME=your-username
NEXTCLOUD_PASSWORD=your-password
```

## Usage

### Naming Templates

Available variables:
- `{description}` - AI-generated description
- `{tags}` - Top AI tags
- `{scene}` - Scene type
- `{date}` - Current date
- `{index}` - Sequential index

**Example:** `{description}_{date}_{index}` → `blue_sky_sunset_20250105_001`

## Deployment

This project uses GitHub Actions for automatic deployment to pi-forge. Push to main branch to trigger deployment.

Access at: https://jspow.lan (LAN only)

## License

MIT License
