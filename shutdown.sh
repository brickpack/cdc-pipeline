#!/bin/bash
# CDC Pipeline Shutdown Script
# Safely stops all services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo "=========================================="
echo "CDC Pipeline Shutdown"
echo "=========================================="
echo ""

# Ask for confirmation
read -p "Are you sure you want to stop all services? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Shutdown cancelled"
    exit 0
fi

# Ask about volumes
read -p "Do you want to remove volumes (all data will be lost)? (y/n) " -n 1 -r
echo
REMOVE_VOLUMES=$REPLY

# Stop monitoring stack
if docker compose -f docker-compose.monitoring.yml ps 2>/dev/null | grep -q "Up"; then
    print_info "Stopping monitoring stack..."
    if [[ $REMOVE_VOLUMES =~ ^[Yy]$ ]]; then
        docker compose -f docker-compose.monitoring.yml down -v
    else
        docker compose -f docker-compose.monitoring.yml down
    fi
    print_info "Monitoring stack stopped"
fi

# Stop core services
print_info "Stopping core services..."
if [[ $REMOVE_VOLUMES =~ ^[Yy]$ ]]; then
    docker compose down -v
    print_warn "All data has been removed"
else
    docker compose down
    print_info "Data volumes preserved"
fi

print_info "CDC Pipeline stopped"
echo ""
echo "To start again, run: ./setup.sh"
