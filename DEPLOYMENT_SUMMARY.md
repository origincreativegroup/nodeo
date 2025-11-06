# jspow Deployment Summary

## Project Overview

**jspow** is an AI-powered image file renaming and organization tool that uses the LLaVA vision model (via Ollama) to automatically analyze images and generate intelligent filenames based on content.

## Architecture

### Components

1. **Backend (FastAPI + Python 3.11)**
   - LLaVA AI integration for image analysis
   - Template-based file renaming engine
   - Nextcloud WebDAV client
   - Cloudflare R2 and Stream integration
   - PostgreSQL for metadata storage
   - Redis for job queuing

2. **Frontend (React 18 + TypeScript)**
   - Image upload and gallery
   - Batch processing interface
   - Template editor with live preview
   - Storage management dashboard
   - Built with Vite and Tailwind CSS

3. **Infrastructure**
   - Docker Compose orchestration
   - Self-hosted GitHub Actions runner
   - Caddy reverse proxy on pi-net
   - Automatic deployments to pi-forge

### Network Topology

```
Internet/LAN
    ↓
pi-net (192.168.50.70)
    ├── Caddy reverse proxy
    ├── DNS (Pi-hole)
    └── VPN (WireGuard)
    ↓
pi-forge (192.168.50.157)
    ├── jspow-app (port 8002)
    ├── PostgreSQL (port 5433)
    ├── Redis (port 6380)
    └── Portainer (port 9000)
    ↓
ai-srv (192.168.50.248)
    └── Ollama + LLaVA (port 11434)
```

## Deployment Instructions

### Prerequisites

1. **On ai-srv:**
   ```bash
   ollama pull llava
   ```

2. **On pi-forge:**
   ```bash
   mkdir -p /home/admin/jspow
   cd /home/admin/jspow
   git clone <repository-url> .
   cp .env.example .env
   # Edit .env with actual credentials
   ```

### First-Time Setup

```bash
# On pi-forge
cd /home/admin/jspow

# Configure environment
nano .env  # Set OLLAMA_HOST, Nextcloud, Cloudflare credentials

# Build and start
docker compose build --no-cache
docker compose up -d

# Verify
docker compose ps
curl http://localhost:8002/health
```

### Configure Reverse Proxy

On pi-net (`/etc/caddy/Caddyfile`):

```caddyfile
jspow.lan {
    tls internal
    encode zstd gzip
    @notlan not remote_ip 192.168.50.0/24
    respond @notlan 403
    reverse_proxy 192.168.50.157:8002
}
```

Reload: `sudo systemctl reload caddy`

### Automated Deployment

Push to main branch triggers GitHub Actions workflow that:
1. Creates deployment backup
2. Syncs code to pi-forge
3. Builds Docker images (ARM64)
4. Deploys containers
5. Runs health checks
6. Rollbacks on failure

## Access URLs

- **Application:** https://jspow.lan (LAN only)
- **API Docs:** https://jspow.lan/docs
- **Portainer:** http://192.168.50.157:9000
- **Ollama API:** http://192.168.50.248:11434

## Key Features

### AI Image Analysis
- Automatic description generation
- Tag extraction
- Object detection
- Scene classification

### Naming Templates

Variables available:
- `{description}` - AI description (first 4 words)
- `{tags}` - Top 3 tags joined with underscores
- `{scene}` - Scene type (indoor/outdoor/etc.)
- `{date}` - Date (YYYYMMDD)
- `{time}` - Time (HHMMSS)
- `{index}` - Zero-padded index (001, 002...)
- `{original}` - Original filename
- `{width}` / `{height}` - Image dimensions

Example: `{description}_{date}_{index}` → `sunset_over_mountains_20250105_001.jpg`

### Storage Integration

- **Nextcloud:** Organize and sync images
- **Cloudflare R2:** Cloud storage with S3-compatible API
- **Cloudflare Stream:** Video hosting and streaming

## Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8002/health

# Container status
docker compose ps

# View logs
docker compose logs -f jspow-app
```

### Database Access

```bash
# Connect to database
docker compose exec postgres psql -U postgres -d jspow

# List tables
\dt

# Query images
SELECT id, original_filename, ai_description FROM images LIMIT 10;
```

## Maintenance

### Update Deployment

```bash
cd /home/admin/jspow
git pull
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Backup Database

```bash
docker compose exec postgres pg_dump -U postgres jspow | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Cleanup

```bash
# Remove old backups (keep last 5)
cd /home/admin/deployments/jspow
ls -t | tail -n +6 | xargs rm -rf

# Prune Docker images
docker image prune -a
```

## Troubleshooting

### Common Issues

1. **Ollama connection failed**
   ```bash
   # Test from pi-forge
   curl http://192.168.50.248:11434/api/tags

   # Check if LLaVA is installed
   curl http://192.168.50.248:11434/api/tags | grep llava
   ```

2. **Container won't start**
   ```bash
   # Check logs
   docker compose logs jspow-app

   # Verify .env file
   cat .env | grep -v PASSWORD
   ```

3. **Database connection error**
   ```bash
   # Restart database
   docker compose restart postgres

   # Check database logs
   docker compose logs postgres
   ```

## Development

### Local Development

1. **Backend:**
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8002
   ```

2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev  # Runs on port 3000, proxies to :8002
   ```

### Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
jspow/
├── app/
│   ├── ai/                   # LLaVA integration
│   ├── storage/              # Nextcloud, R2, Stream
│   ├── services/             # Rename engine, templates
│   ├── config.py
│   ├── database.py
│   └── models.py
├── frontend/
│   └── src/
│       ├── pages/            # React pages
│       └── services/         # API client
├── .github/workflows/        # CI/CD
├── docker-compose.yml
├── Dockerfile
├── main.py
└── requirements.txt
```

## Next Steps

1. **Install LLaVA on ai-srv** (if not already installed)
2. **Deploy to pi-forge** using instructions above
3. **Configure Caddy** on pi-net for https://jspow.lan
4. **Set up GitHub Actions runner** for automated deployments
5. **Configure Nextcloud and Cloudflare** credentials in `.env`

## Reference

- **Based on js-craw infrastructure pattern**
- **LLaVA model:** Multimodal vision-language model
- **Deployment:** Self-hosted on pi-forge (ARM64)
- **CI/CD:** GitHub Actions with self-hosted runner
- **Access:** LAN-only via Caddy reverse proxy

---

Generated with Claude Code
