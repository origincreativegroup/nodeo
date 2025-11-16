# ✅ Claude Code Setup Complete for nodeo

## 📁 Files Created

1. **`deploy-to-pi-forge.sh`** - Automated deployment script
2. **`CLAUDE-CODE-SETUP.md`** - Complete setup documentation
3. **`.env.claude-code`** - Environment variables template
4. **`QUICK-START-CLAUDE.md`** - Quick reference guide

## 🎯 What You Need To Do Now

### Step 1: Setup SSH Access (5 minutes)

Open terminal and run:

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "claude-code-nodeo" -f ~/.ssh/pi-forge-nodeo

# Copy to pi-forge (will prompt for password once)
ssh-copy-id -i ~/.ssh/pi-forge-nodeo.pub admin@192.168.50.157

# Test connection (should work without password)
ssh -i ~/.ssh/pi-forge-nodeo admin@192.168.50.157 "docker ps"
```

Add to `~/.ssh/config`:
```
Host pi-forge
    HostName 192.168.50.157
    User admin
    IdentityFile ~/.ssh/pi-forge-nodeo
```

### Step 2: Create Cloud Environment in Claude Code

1. **Open Claude Code** and click "New cloud environment"
2. **Name:** `nodeo-pi-forge`
3. **Network Access:** Select "Full network access"
4. **Environment Variables:** Copy-paste from `.env.claude-code` file
5. Click **"Create environment"**

### Step 3: Test Deployment

```bash
cd /Users/origin/GitHub/nodeo

# Test connection
./deploy-to-pi-forge.sh --status

# Quick test deploy
./deploy-to-pi-forge.sh --quick
```

## 🚀 Usage

### Development Cycle (FAST)

```bash
# 1. Edit code in Claude Code
# 2. Quick deploy (10 seconds)
./deploy-to-pi-forge.sh --quick

# 3. View logs
./deploy-to-pi-forge.sh --logs

# 4. Test at https://nodeo.lan
```

### Common Commands

```bash
./deploy-to-pi-forge.sh --quick   # Fast iteration (sync + restart)
./deploy-to-pi-forge.sh           # Full rebuild
./deploy-to-pi-forge.sh --logs    # View logs
./deploy-to-pi-forge.sh --status  # Check containers
./deploy-to-pi-forge.sh --health  # Health check
./deploy-to-pi-forge.sh --help    # All options
```

## 🔗 Access Points

After deployment:
- **Main App:** https://nodeo.lan
- **Direct:** http://192.168.50.157:8002
- **API:** https://nodeo.lan/api
- **Health:** https://nodeo.lan/health

## 🏗️ Architecture

```
Your Machine (mac-forge)
    │
    │ SSH/rsync (deploy script)
    ↓
Pi-Forge (192.168.50.157)
    ├─ nodeo-app (port 8002)
    ├─ PostgreSQL (port 5433)
    ├─ Redis (port 6380)
    │
    ↓ Proxied via Caddy
Pi-Net (192.168.50.70)
    └─ Reverse Proxy: https://nodeo.lan → 192.168.50.157:8002

AI-Srv (192.168.50.248)
    └─ Ollama API: https://ollama.nexus.lan
```

## 📝 Environment Variables Reference

Key variables in `.env.claude-code`:

```bash
# Deployment target
PI_FORGE_HOST=192.168.50.157
PI_FORGE_USER=admin

# Services
nodeo_URL=https://nodeo.lan
OLLAMA_HOST=https://ollama.nexus.lan
NEXTCLOUD_URL=https://nextcloud.lan

# Database
POSTGRES_HOST=192.168.50.157
POSTGRES_PORT=5433

# Redis
REDIS_HOST=192.168.50.157
REDIS_PORT=6380
```

## 🔒 Security Notes

- SSH key authentication (no passwords)
- `.env` files excluded from deployment
- Credentials stored only on pi-forge
- TLS via Caddy reverse proxy

## 🐛 Troubleshooting

**Can't connect to pi-forge?**
```bash
ssh pi-forge "echo Connected"
ping 192.168.50.157
```

**Deployment fails?**
```bash
./deploy-to-pi-forge.sh --status
./deploy-to-pi-forge.sh --logs
```

**Service not accessible?**
```bash
./deploy-to-pi-forge.sh --health
curl -k https://nodeo.lan/health
```

## 📚 Documentation

- **Quick Start:** `QUICK-START-CLAUDE.md`
- **Full Setup:** `CLAUDE-CODE-SETUP.md`
- **Deployment Script:** `deploy-to-pi-forge.sh --help`
- **Main README:** `README.md`

## ✨ Benefits

- ⚡ **Fast iteration:** 10 second deployments with `--quick`
- 🔄 **Live testing:** Deploy directly to pi-forge
- 📊 **Real environment:** Test with real database, Redis, Ollama
- 🔍 **Easy debugging:** One command to view logs
- 🌐 **Full stack:** All services accessible via Caddy reverse proxy

## 🎉 Ready to Go!

Once you complete Steps 1-3 above, you're ready to:
1. Make code changes in Claude Code
2. Run `./deploy-to-pi-forge.sh --quick`
3. Test at https://nodeo.lan
4. Iterate rapidly!

---

**Questions?** Check the full documentation in `CLAUDE-CODE-SETUP.md`
