# Pi-Forge Deployment Guide for nodeo

This document describes how to deploy nodeo on pi-forge using the same infrastructure pattern as js-craw.

## Infrastructure Overview

**Network:**
- **pi-net** (192.168.50.70): Reverse proxy, DNS, VPN gateway
- **pi-forge** (192.168.50.157): Docker host (Raspberry Pi 5, 8GB RAM, ARM64)
- **ai-srv** (192.168.50.248): Ollama + LLaVA model server

**Access:**
- Local: `http://192.168.50.157:8002`
- Proxied: `https://nodeo.lan` (via Caddy on pi-net)

## Prerequisites

### On ai-srv (Ollama Setup)

1. **Install LLaVA model**
   ```bash
   ssh admin@ai-srv
   ollama pull llava
   ollama list  # Verify llava is installed
   ```

2. **Verify Ollama is accessible**
   ```bash
   curl http://192.168.50.248:11434/api/tags
   ```

### On pi-forge

1. **Create project directory**
   ```bash
   ssh admin@pi-forge
   mkdir -p /home/admin/nodeo
   cd /home/admin/nodeo
   ```

2. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/nodeo.git .
   ```

3. **Create .env file**
   ```bash
   cp .env.example .env
   nano .env
   ```

   **Minimal .env configuration:**
   ```env
   # Application
   SECRET_KEY=your-secret-key-min-32-chars-change-this
   DEBUG=false

   # Database (use container defaults)
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/nodeo

   # Redis (use container defaults)
   REDIS_URL=redis://redis:6379/0

   # Ollama (required - points to ai-srv)
   OLLAMA_HOST=http://192.168.50.248:11434
   OLLAMA_MODEL=llava
   OLLAMA_TIMEOUT=120

   # Nextcloud (configure if using)
   NEXTCLOUD_URL=https://nextcloud.lan
   NEXTCLOUD_USERNAME=admin
   NEXTCLOUD_PASSWORD=your-nextcloud-password
   NEXTCLOUD_BASE_PATH=/nodeo

   # Cloudflare R2 (configure if using)
   CLOUDFLARE_R2_ACCOUNT_ID=
   CLOUDFLARE_R2_ACCESS_KEY_ID=
   CLOUDFLARE_R2_SECRET_ACCESS_KEY=
   CLOUDFLARE_R2_BUCKET=nodeo-images
   CLOUDFLARE_R2_ENDPOINT=

   # Cloudflare Stream (configure if using)
   CLOUDFLARE_STREAM_ACCOUNT_ID=
   CLOUDFLARE_STREAM_API_TOKEN=
   ```

4. **Create deployment backups directory**
   ```bash
   mkdir -p /home/admin/deployments/nodeo
   ```

## Manual Deployment

### First Deployment

```bash
cd /home/admin/nodeo

# Build containers
docker compose build --no-cache

# Start services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f nodeo-app

# Test health endpoint
curl http://localhost:8002/health
```

### Update Deployment

```bash
cd /home/admin/nodeo

# Pull latest changes
git pull

# Rebuild and restart
docker compose down
docker compose build --no-cache
docker compose up -d

# Verify
curl http://localhost:8002/health
```

## Automated Deployment (GitHub Actions)

### Setup Self-Hosted Runner

1. **Install runner on pi-forge**

   Follow the js-craw pattern - the runner should already be configured if you have js-craw running.

   If not, create a new runner:
   ```bash
   cd /home/admin/docker/github-runner

   # Update docker-compose.yml to add nodeo runner
   # Or create a new runner container
   ```

2. **Workflow triggers on push to main**

   The `.github/workflows/deploy-pi-forge.yml` workflow will:
   - Run on self-hosted runner (pi-forge)
   - Create backup of current deployment
   - Sync code to `/home/admin/nodeo`
   - Build Docker images
   - Deploy containers
   - Run health checks
   - Rollback on failure

### Deployment Flow

```
1. Developer pushes to main
   ↓
2. GitHub triggers workflow
   ↓
3. Self-hosted runner (pi-forge) picks up job
   ↓
4. Backup current deployment
   ↓
5. Sync code (preserve .env)
   ↓
6. Build: docker compose build --no-cache
   ↓
7. Deploy: docker compose up -d
   ↓
8. Health check: curl http://localhost:8002/health
   ↓
9. Success: Create deployment marker
   OR
   Failure: Rollback to backup
```

## Pi-Net Reverse Proxy Configuration

### Add Caddy Route

SSH to pi-net and edit Caddyfile:

```bash
ssh admin@pi-net
sudo nano /etc/caddy/Caddyfile
```

Add this block:

```caddyfile
nodeo.lan {
    tls internal
    encode zstd gzip

    # LAN-only access
    @notlan not remote_ip 192.168.50.0/24
    respond @notlan 403

    # Proxy to pi-forge
    reverse_proxy 192.168.50.157:8002
}
```

Reload Caddy:

```bash
sudo systemctl reload caddy
```

Verify:

```bash
curl -I https://nodeo.lan
```

## Container Management

### Using Docker Compose

```bash
# View status
docker compose ps

# View logs
docker compose logs -f nodeo-app
docker compose logs -f nodeo-postgres
docker compose logs -f nodeo-redis

# Restart service
docker compose restart nodeo-app

# Stop all
docker compose down

# Start all
docker compose up -d

# Rebuild specific service
docker compose up -d --build nodeo-app
```

### Using Portainer

Access Portainer at: http://192.168.50.157:9000

1. Navigate to **Stacks** → **nodeo**
2. View container status, logs, stats
3. Restart containers
4. View resource usage

## Monitoring & Logs

### Application Logs

```bash
# Follow logs
docker compose logs -f nodeo-app

# Last 100 lines
docker compose logs --tail=100 nodeo-app

# Search logs
docker compose logs nodeo-app | grep ERROR
```

### Database Logs

```bash
docker compose logs nodeo-postgres
```

### Health Monitoring

```bash
# Health check
curl http://localhost:8002/health

# API docs
curl http://localhost:8002/docs

# Database connection test
docker exec nodeo-postgres psql -U postgres -d nodeo -c "SELECT 1;"
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs nodeo-app

# Check if port is in use
sudo netstat -tlnp | grep 8002

# Verify .env file
cat .env | grep -v PASSWORD

# Test database connection
docker compose exec postgres psql -U postgres -d nodeo
```

### Ollama connection issues

```bash
# Test Ollama from pi-forge
curl http://192.168.50.248:11434/api/tags

# Test from container
docker compose exec nodeo-app curl http://192.168.50.248:11434/api/tags

# Check if LLaVA is installed
curl http://192.168.50.248:11434/api/tags | grep llava
```

### Database issues

```bash
# Connect to database
docker compose exec postgres psql -U postgres -d nodeo

# Check tables
\dt

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

### Rebuild from scratch

```bash
cd /home/admin/nodeo

# Stop and remove everything
docker compose down -v

# Remove images
docker compose images -q | xargs docker rmi

# Rebuild
docker compose build --no-cache
docker compose up -d
```

## Backup & Restore

### Backup Database

```bash
# Backup to file
docker compose exec postgres pg_dump -U postgres nodeo > backup_$(date +%Y%m%d).sql

# Backup with docker
docker compose exec postgres pg_dump -U postgres nodeo | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore Database

```bash
# Restore from backup
cat backup_20250105.sql | docker compose exec -T postgres psql -U postgres nodeo

# Restore from gzipped backup
gunzip -c backup_20250105.sql.gz | docker compose exec -T postgres psql -U postgres nodeo
```

### Backup Uploaded Images

```bash
# Backup uploads directory
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz -C /home/admin/nodeo uploads/

# Or use Docker volume backup
docker run --rm -v nodeo_uploads_data:/data -v $(pwd):/backup alpine tar czf /backup/uploads_backup.tar.gz -C /data .
```

## Performance Tuning

### Database

Edit `docker-compose.yml` to add PostgreSQL tuning:

```yaml
postgres:
  environment:
    - POSTGRES_MAX_CONNECTIONS=100
  command:
    - "postgres"
    - "-c"
    - "shared_buffers=256MB"
    - "-c"
    - "effective_cache_size=512MB"
```

### Application

Increase worker processes by modifying `Dockerfile`:

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002", "--workers", "4"]
```

## Security

### Secure .env file

```bash
chmod 600 /home/admin/nodeo/.env
```

### Update secrets

```bash
# Generate new secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env
nano .env
```

### Firewall (via pi-net)

The Caddy reverse proxy on pi-net already restricts access to LAN only. To allow VPN access:

```caddyfile
nodeo.lan {
    # Allow LAN and VPN
    @notauthorized not remote_ip 192.168.50.0/24 10.0.0.0/24
    respond @notauthorized 403

    reverse_proxy 192.168.50.157:8002
}
```

## Maintenance

### Update Docker images

```bash
cd /home/admin/nodeo

# Pull latest base images
docker compose pull

# Rebuild
docker compose build --no-cache
docker compose up -d
```

### Clean up old images

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune
```

### Cleanup deployment backups

```bash
cd /home/admin/deployments/nodeo

# Keep only last 5
ls -t | tail -n +6 | xargs rm -rf
```

## Support

For issues specific to pi-forge deployment, check:
- js-craw deployment at `/home/admin/js-craw` for reference
- Portainer logs
- `/var/log/docker/` on pi-forge
- GitHub Actions workflow runs

## Quick Reference

**SSH Access:**
```bash
ssh admin@pi-forge
ssh admin@pi-net
ssh admin@ai-srv
```

**Key URLs:**
- App: https://nodeo.lan
- API Docs: https://nodeo.lan/docs
- Portainer: http://192.168.50.157:9000
- Ollama: http://192.168.50.248:11434

**Key Directories:**
- Code: `/home/admin/nodeo`
- Backups: `/home/admin/deployments/nodeo`
- Logs: `docker compose logs -f`
