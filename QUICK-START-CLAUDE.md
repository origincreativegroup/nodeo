# Quick Start: Claude Code + jspow + Pi-Forge

## 🚀 Setup (One-Time)

### 1. Setup SSH Access
```bash
ssh-keygen -t ed25519 -C "claude-code-jspow" -f ~/.ssh/pi-forge-jspow
ssh-copy-id -i ~/.ssh/pi-forge-jspow.pub admin@192.168.50.157
ssh -i ~/.ssh/pi-forge-jspow admin@192.168.50.157 "docker ps"
```

### 2. Add to ~/.ssh/config
```
Host pi-forge
    HostName 192.168.50.157
    User admin
    IdentityFile ~/.ssh/pi-forge-jspow
```

### 3. Create Claude Code Cloud Environment
- **Name:** `jspow-pi-forge`
- **Network Access:** `Full network access` ✓
- **Environment Variables:** Copy from `.env.claude-code`

## ⚡ Development Workflow

### Fast Iteration (Most Common)
```bash
# 1. Make code changes
# 2. Quick deploy (10 seconds)
./deploy-to-pi-forge.sh --quick

# 3. Check logs
./deploy-to-pi-forge.sh --logs

# 4. Test
open https://jspow.lan
```

### Full Deploy (After Dependencies Change)
```bash
./deploy-to-pi-forge.sh
```

## 📋 Common Commands

| Command | Description | Speed |
|---------|-------------|-------|
| `./deploy-to-pi-forge.sh --quick` | Sync + restart | ~10s |
| `./deploy-to-pi-forge.sh` | Full rebuild + deploy | ~2-3min |
| `./deploy-to-pi-forge.sh --logs` | View logs | Instant |
| `./deploy-to-pi-forge.sh --status` | Container status | Instant |
| `./deploy-to-pi-forge.sh --health` | Health check | Instant |
| `./deploy-to-pi-forge.sh --restart` | Restart only | ~5s |

## 🔗 Access URLs

- **Main:** https://jspow.lan
- **Direct:** http://192.168.50.157:8002
- **API:** https://jspow.lan/api
- **Health:** https://jspow.lan/health

## 🐛 Troubleshooting

```bash
# Can't connect?
ssh pi-forge "echo Connected"

# Containers not running?
./deploy-to-pi-forge.sh --status

# Check logs
./deploy-to-pi-forge.sh --logs

# Test health
./deploy-to-pi-forge.sh --health
```

## 💡 Tips

- Use `--quick` for 95% of iterations (fast!)
- Logs auto-scroll (Ctrl+C to exit)
- SSH config makes `pi-forge` an alias
- Database persists across restarts
- `.env` is excluded from sync (secure)

## 📚 Full Docs

See `CLAUDE-CODE-SETUP.md` for complete documentation.
