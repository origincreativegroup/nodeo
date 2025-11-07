# Claude Code Cloud Environment Setup for jspow

This guide configures Claude Code to use **pi-forge** as a live testing/deployment target for rapid jspow development.

## 1. Cloud Environment Configuration

### In Claude Code Dialog:

**Name:** `jspow-pi-forge`

**Network Access:** `Full network access` ✓

**Environment Variables:**

```bash
# Pi-Forge Target
PI_FORGE_HOST=192.168.50.157
PI_FORGE_USER=admin
PI_FORGE_DOCKER_HOST=ssh://admin@192.168.50.157

# jspow Service URLs
JSPOW_URL=https://jspow.lan
JSPOW_API=https://jspow.lan/api
JSPOW_PORT=8002

# Database (PostgreSQL on pi-forge)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/jspow
POSTGRES_HOST=192.168.50.157
POSTGRES_PORT=5433
POSTGRES_DB=jspow
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis (on pi-forge)
REDIS_HOST=192.168.50.157
REDIS_PORT=6380
REDIS_URL=redis://192.168.50.157:6380/0

# Ollama API (ai-srv via reverse proxy)
OLLAMA_HOST=https://ollama.nexus.lan
OLLAMA_API=https://ollama.nexus.lan/api
OLLAMA_MODEL=llava

# Nextcloud Integration (pi-forge)
NEXTCLOUD_URL=https://nextcloud.lan
NEXTCLOUD_USERNAME=your_username
NEXTCLOUD_PASSWORD=your_password
NEXTCLOUD_BASE_PATH=/jspow

# Cloudflare R2 (Optional)
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_key
CLOUDFLARE_R2_BUCKET=jspow-images
CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com

# Cloudflare Stream (Optional)
CLOUDFLARE_STREAM_ACCOUNT_ID=your_account_id
CLOUDFLARE_STREAM_API_TOKEN=your_api_token

# Storage & Processing
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=100
MAX_BATCH_SIZE=50
PROCESS_TIMEOUT_SECONDS=300

# Application
SECRET_KEY=change-me-to-random-string-min-32-chars
DEBUG=true
APP_NAME=jspow
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=8002
```

## 2. SSH Access Setup

### Generate SSH Key for Pi-Forge

On your **development machine** (mac-forge or local):

```bash
# Generate dedicated SSH key for jspow deployments
ssh-keygen -t ed25519 -C "claude-code-jspow" -f ~/.ssh/pi-forge-jspow

# Copy public key to pi-forge
ssh-copy-id -i ~/.ssh/pi-forge-jspow.pub admin@192.168.50.157

# Test connection
ssh -i ~/.ssh/pi-forge-jspow admin@192.168.50.157 "docker ps"
```

### Configure SSH Config

Add to `~/.ssh/config`:

```
Host pi-forge
    HostName 192.168.50.157
    User admin
    IdentityFile ~/.ssh/pi-forge-jspow
    StrictHostKeyChecking no
    ServerAliveInterval 60
    ServerAliveCountMax 3
```

Now you can connect with: `ssh pi-forge`

## 3. Deployment Script Usage

The `deploy-to-pi-forge.sh` script automates deployment to pi-forge.

### Quick Reference

```bash
# Full deployment (sync + build + deploy)
./deploy-to-pi-forge.sh

# Quick deployment (sync + restart, no rebuild) - FASTEST
./deploy-to-pi-forge.sh --quick

# Build containers only
./deploy-to-pi-forge.sh --build

# Restart containers only
./deploy-to-pi-forge.sh --restart

# View logs
./deploy-to-pi-forge.sh --logs

# Check status
./deploy-to-pi-forge.sh --status

# Health check
./deploy-to-pi-forge.sh --health

# Stop containers
./deploy-to-pi-forge.sh --stop

# Show help
./deploy-to-pi-forge.sh --help
```

### Typical Claude Code Workflow

1. **Make code changes** in Claude Code
2. **Quick deploy:** `./deploy-to-pi-forge.sh --quick` (syncs code + restarts containers)
3. **Check logs:** `./deploy-to-pi-forge.sh --logs`
4. **Test:** Access https://jspow.lan or http://192.168.50.157:8002
5. **Iterate:** Repeat steps 1-4

For **major changes** (Dockerfile, dependencies):
```bash
./deploy-to-pi-forge.sh  # Full rebuild
```

## 4. Claude Code Commands

When working in Claude Code, use these commands:

### Deploy & Test
```bash
# Quick test iteration
bash deploy-to-pi-forge.sh --quick

# Full rebuild (after dependency changes)
bash deploy-to-pi-forge.sh

# Check if services are healthy
bash deploy-to-pi-forge.sh --health
```

### Monitor
```bash
# Watch logs
bash deploy-to-pi-forge.sh --logs

# Check container status
bash deploy-to-pi-forge.sh --status

# SSH into pi-forge for debugging
ssh pi-forge "cd /home/admin/jspow && docker compose exec jspow-app bash"
```

### Database Access
```bash
# Connect to PostgreSQL on pi-forge
ssh pi-forge "docker exec -it jspow-postgres psql -U postgres -d jspow"

# Connect to Redis
ssh pi-forge "docker exec -it jspow-redis redis-cli"
```

## 5. Access URLs

After deployment, jspow is accessible at:

- **Reverse Proxy (HTTPS):** https://jspow.lan
- **Direct Access (HTTP):** http://192.168.50.157:8002
- **API Endpoint:** https://jspow.lan/api
- **Health Check:** https://jspow.lan/health

## 6. Development Workflow

### Typical Development Cycle

1. **Edit code** in Claude Code
2. **Deploy changes:**
   ```bash
   ./deploy-to-pi-forge.sh --quick
   ```
3. **Test in browser:** Open https://jspow.lan
4. **Check logs if needed:**
   ```bash
   ./deploy-to-pi-forge.sh --logs
   ```
5. **Iterate:** Make more changes and repeat

### When to Use Full Deploy vs Quick Deploy

**Quick Deploy (`--quick`):**
- Code changes in Python/FastAPI
- Template/HTML changes
- Configuration changes (.env)
- 95% of development iterations
- **~10 seconds total**

**Full Deploy (default):**
- Changed `requirements.txt` or `package.json`
- Modified `Dockerfile`
- Major dependency updates
- **~2-3 minutes total**

## 7. Troubleshooting

### Cannot Connect to Pi-Forge

```bash
# Test SSH connection
ssh pi-forge "echo 'Connected'"

# Check if pi-forge is reachable
ping 192.168.50.157

# Verify VPN connection (if remote)
wg show
```

### Containers Not Starting

```bash
# Check logs
./deploy-to-pi-forge.sh --logs

# Check container status
./deploy-to-pi-forge.sh --status

# SSH into pi-forge and check manually
ssh pi-forge "cd /home/admin/jspow && docker compose ps"
ssh pi-forge "cd /home/admin/jspow && docker compose logs"
```

### Service Not Accessible

```bash
# Check health
./deploy-to-pi-forge.sh --health

# Test direct connection
curl -v http://192.168.50.157:8002/health

# Test via reverse proxy
curl -k -v https://jspow.lan/health

# Check Caddy on pi-net
ssh admin@192.168.50.70 "sudo journalctl -u caddy -f"
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
ssh pi-forge "docker exec jspow-postgres psql -U postgres -d jspow -c 'SELECT 1;'"

# Check if database is running
ssh pi-forge "docker compose ps postgres"

# View database logs
ssh pi-forge "docker compose logs postgres"
```

## 8. Security Notes

- **Never commit `.env` files** with real credentials
- The deployment script **excludes** `.env` from sync
- Create `.env` on pi-forge manually or use environment variables in docker-compose
- SSH keys are used for authentication (no password prompts)
- All sensitive values should be in `.env.example` as templates

## 9. Network Architecture

```
┌─────────────────┐
│   Development   │
│   Machine       │
│  (mac-forge)    │
└────────┬────────┘
         │ SSH/rsync
         ↓
┌─────────────────────────────────────────┐
│         Pi-Forge (192.168.50.157)       │
│  ┌───────────┐  ┌────────┐  ┌────────┐ │
│  │ jspow-app │→ │ Redis  │  │Postgres│ │
│  │ (port     │  │ (6380) │  │ (5433) │ │
│  │  8002)    │  └────────┘  └────────┘ │
│  └─────┬─────┘                          │
└────────┼────────────────────────────────┘
         │
         ↓ Proxied via Caddy
┌─────────────────┐
│     Pi-Net      │
│ (192.168.50.70) │  Reverse Proxy
│  Caddy Proxy    │  https://jspow.lan → 192.168.50.157:8002
└─────────────────┘
         │
         ↓ AI Services
┌─────────────────┐
│     AI-Srv      │
│(192.168.50.248) │  Ollama API
│ Ollama/LLaVA    │  https://ollama.nexus.lan
└─────────────────┘
```

## 10. Tips for Claude Code

When Claude Code is working on jspow:

1. **Use `--quick` by default** - It's much faster for code iterations
2. **Check logs frequently** - `./deploy-to-pi-forge.sh --logs`
3. **Test health after deploy** - `./deploy-to-pi-forge.sh --health`
4. **Access via HTTPS** - https://jspow.lan (Caddy handles TLS)
5. **Database is persistent** - Data survives container restarts

### Example Claude Code Session

```bash
# 1. Make changes to app code
# (Claude edits files in /Users/origin/GitHub/jspow)

# 2. Quick deploy
bash deploy-to-pi-forge.sh --quick

# 3. Check if healthy
bash deploy-to-pi-forge.sh --health

# 4. View logs
bash deploy-to-pi-forge.sh --logs

# 5. Test in browser or via API
curl -k https://jspow.lan/api/health
```

## 11. Next Steps

1. **Create the cloud environment** in Claude Code with the variables above
2. **Set up SSH keys** using the commands in section 2
3. **Test the deployment script:** `./deploy-to-pi-forge.sh --status`
4. **Start developing!** Claude Code can now deploy to pi-forge instantly

---

**Questions?** Check the main jspow README.md or Nexus.lan documentation in `/Users/origin/GitHub/Nexus.lan/`
