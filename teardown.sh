#!/bin/bash
# CDC Pipeline Complete Teardown Script
# Removes ALL containers, volumes, networks, and generated files

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}==>${NC} $1"
}

echo "=========================================="
echo "CDC Pipeline Complete Teardown"
echo "=========================================="
echo ""
print_warn "This will remove:"
echo "  • All Docker containers"
echo "  • All Docker volumes (ALL DATA WILL BE LOST)"
echo "  • All Docker networks"
echo "  • Generated connector configurations"
echo "  • Temporary files and logs"
echo ""
print_error "This action cannot be undone!"
echo ""

# Ask for confirmation
read -p "Are you absolutely sure you want to proceed? Type 'yes' to confirm: " -r
echo
if [[ ! $REPLY == "yes" ]]; then
    print_info "Teardown cancelled"
    exit 0
fi

echo ""
print_step "Step 1: Stopping all running containers..."

# Stop monitoring stack if running
if docker compose -f docker-compose.monitoring.yml ps 2>/dev/null | grep -q "Up"; then
    print_info "Stopping monitoring stack..."
    docker compose -f docker-compose.monitoring.yml down -v --remove-orphans 2>/dev/null || true
    print_info "✓ Monitoring stack stopped"
else
    print_info "Monitoring stack not running"
fi

# Stop core services
print_info "Stopping core services..."
docker compose down -v --remove-orphans 2>/dev/null || true
print_info "✓ Core services stopped"

echo ""
print_step "Step 2: Removing all project containers..."

# Remove any containers with our project name
CONTAINERS=$(docker ps -a --filter "name=cdc-pipeline" --filter "name=postgres" --filter "name=kafka" --filter "name=zookeeper" --filter "name=connect" --filter "name=schema-registry" --filter "name=cdc-consumer" --filter "name=linkedin-ingestion" --filter "name=grafana" --filter "name=prometheus" --filter "name=loki" -q 2>/dev/null || true)

if [ -n "$CONTAINERS" ]; then
    print_info "Removing containers: $(echo $CONTAINERS | wc -w) found"
    docker rm -f $CONTAINERS 2>/dev/null || true
    print_info "✓ Containers removed"
else
    print_info "No containers to remove"
fi

echo ""
print_step "Step 3: Removing all project volumes..."

# Remove all volumes
VOLUMES=$(docker volume ls --filter "name=cdc-pipeline" -q 2>/dev/null || true)
if [ -n "$VOLUMES" ]; then
    print_info "Removing volumes: $(echo $VOLUMES | wc -w) found"
    docker volume rm $VOLUMES 2>/dev/null || true
    print_info "✓ Volumes removed"
else
    print_info "No volumes to remove"
fi

echo ""
print_step "Step 4: Removing project networks..."

# Remove networks
NETWORKS=$(docker network ls --filter "name=cdc" -q 2>/dev/null || true)
if [ -n "$NETWORKS" ]; then
    print_info "Removing networks: $(echo $NETWORKS | wc -w) found"
    docker network rm $NETWORKS 2>/dev/null || true
    print_info "✓ Networks removed"
else
    print_info "No networks to remove"
fi

echo ""
print_step "Step 5: Cleaning up generated files..."

# Remove generated connector configuration
if [ -f "connectors/postgres-connector.json" ]; then
    rm -f connectors/postgres-connector.json
    print_info "✓ Removed generated connector config"
fi

# Clean up any __pycache__ directories
if [ -d "consumer/__pycache__" ]; then
    rm -rf consumer/__pycache__
    print_info "✓ Removed Python cache"
fi

if [ -d "api-ingestion/__pycache__" ]; then
    rm -rf api-ingestion/__pycache__
    print_info "✓ Removed Python cache"
fi

# Clean up any .pyc files
find . -type f -name "*.pyc" -delete 2>/dev/null || true

print_info "Generated files cleaned"

echo ""
print_step "Step 6: Optional cleanup..."

# Ask about .env file
echo ""
read -p "Do you want to remove the .env file? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f ".env" ]; then
        rm -f .env
        print_warn "✓ Removed .env file (you'll need to recreate it)"
    else
        print_info ".env file not found"
    fi
else
    print_info "Keeping .env file"
fi

echo ""
print_step "Step 7: Docker system cleanup (optional)..."

# Ask about Docker system prune
echo ""
print_info "You can optionally run 'docker system prune' to free up more space."
read -p "Run Docker system prune? This removes unused images and build cache. (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_info "Running Docker system prune..."
    docker system prune -f
    print_info "✓ Docker system pruned"
else
    print_info "Skipping Docker system prune"
fi

echo ""
echo "=========================================="
print_info "Teardown complete!"
echo "=========================================="
echo ""
print_info "Summary:"
echo "  ✓ All containers stopped and removed"
echo "  ✓ All volumes deleted (data lost)"
echo "  ✓ All networks removed"
echo "  ✓ Generated files cleaned"
echo ""
print_info "To start fresh, run: ./setup.sh"
echo ""
