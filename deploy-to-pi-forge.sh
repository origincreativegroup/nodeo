#!/bin/bash
#
# nodeo Quick Deploy to Pi-Forge
# Usage: ./deploy-to-pi-forge.sh [--build|--restart|--logs|--status]
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PI_FORGE_HOST="${PI_FORGE_HOST:-192.168.50.157}"
PI_FORGE_USER="${PI_FORGE_USER:-admin}"
REMOTE_PATH="/home/admin/nodeo"
LOCAL_PATH="$(pwd)"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check SSH connection
check_connection() {
    log_info "Checking connection to pi-forge..."
    if ssh -o ConnectTimeout=5 "${PI_FORGE_USER}@${PI_FORGE_HOST}" "echo 'Connected'" &>/dev/null; then
        log_success "Connected to pi-forge (${PI_FORGE_HOST})"
        return 0
    else
        log_error "Cannot connect to pi-forge. Check SSH keys and network."
        return 1
    fi
}

# Sync code to pi-forge
sync_code() {
    log_info "Syncing code to pi-forge..."

    # Exclude unnecessary files
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude '.env' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude '.pytest_cache' \
        --exclude 'uploads' \
        --exclude '.venv' \
        "${LOCAL_PATH}/" \
        "${PI_FORGE_USER}@${PI_FORGE_HOST}:${REMOTE_PATH}/"

    log_success "Code synced to pi-forge:${REMOTE_PATH}"
}

# Build containers on pi-forge
build_containers() {
    log_info "Building Docker containers on pi-forge..."

    ssh "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose build --no-cache"

    log_success "Containers built successfully"
}

# Deploy (restart) containers
deploy_containers() {
    log_info "Deploying containers on pi-forge..."

    ssh "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose up -d"

    log_success "Containers deployed and running"
}

# Restart containers (without rebuild)
restart_containers() {
    log_info "Restarting containers on pi-forge..."

    ssh "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose restart"

    log_success "Containers restarted"
}

# Show container status
show_status() {
    log_info "Container status on pi-forge:"
    echo ""

    ssh "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose ps"
}

# Show logs
show_logs() {
    log_info "Showing logs from pi-forge (Ctrl+C to exit):"
    echo ""

    ssh -t "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose logs -f --tail=50"
}

# Stop containers
stop_containers() {
    log_info "Stopping containers on pi-forge..."

    ssh "${PI_FORGE_USER}@${PI_FORGE_HOST}" "cd ${REMOTE_PATH} && docker compose down"

    log_success "Containers stopped"
}

# Health check
health_check() {
    log_info "Checking service health..."
    echo ""

    # Check if nodeo is responding
    if curl -s -o /dev/null -w "%{http_code}" "http://${PI_FORGE_HOST}:8002/health" | grep -q "200"; then
        log_success "nodeo API is healthy (http://${PI_FORGE_HOST}:8002)"
    else
        log_warn "nodeo API not responding on port 8002"
    fi

    # Check via Caddy reverse proxy
    if curl -k -s -o /dev/null -w "%{http_code}" "https://nodeo.lan/health" | grep -q "200"; then
        log_success "nodeo accessible via reverse proxy (https://nodeo.lan)"
    else
        log_warn "nodeo not accessible via Caddy reverse proxy"
    fi
}

# Main deployment workflow
full_deploy() {
    log_info "Starting full deployment to pi-forge..."
    echo ""

    check_connection || exit 1
    sync_code
    build_containers
    deploy_containers
    sleep 5
    show_status
    echo ""
    health_check

    echo ""
    log_success "Deployment complete!"
    log_info "Access nodeo at: https://nodeo.lan"
    log_info "Direct access: http://${PI_FORGE_HOST}:8002"
}

# Quick deploy (sync + restart, no rebuild)
quick_deploy() {
    log_info "Starting quick deployment (no rebuild)..."
    echo ""

    check_connection || exit 1
    sync_code
    restart_containers
    sleep 3
    show_status
    echo ""
    health_check

    echo ""
    log_success "Quick deployment complete!"
}

# Parse arguments
case "${1:-}" in
    --build)
        check_connection || exit 1
        build_containers
        ;;
    --restart)
        check_connection || exit 1
        restart_containers
        ;;
    --logs)
        check_connection || exit 1
        show_logs
        ;;
    --status)
        check_connection || exit 1
        show_status
        ;;
    --stop)
        check_connection || exit 1
        stop_containers
        ;;
    --health)
        check_connection || exit 1
        health_check
        ;;
    --quick)
        quick_deploy
        ;;
    --help)
        echo "nodeo Deployment Script"
        echo ""
        echo "Usage: ./deploy-to-pi-forge.sh [OPTION]"
        echo ""
        echo "Options:"
        echo "  (no args)   Full deployment (sync + build + deploy)"
        echo "  --quick     Quick deployment (sync + restart, no rebuild)"
        echo "  --build     Build containers only"
        echo "  --restart   Restart containers only"
        echo "  --logs      Show container logs"
        echo "  --status    Show container status"
        echo "  --stop      Stop all containers"
        echo "  --health    Check service health"
        echo "  --help      Show this help message"
        echo ""
        echo "Environment variables:"
        echo "  PI_FORGE_HOST=${PI_FORGE_HOST}"
        echo "  PI_FORGE_USER=${PI_FORGE_USER}"
        echo "  REMOTE_PATH=${REMOTE_PATH}"
        ;;
    *)
        full_deploy
        ;;
esac
