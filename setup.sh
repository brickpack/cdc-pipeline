#!/bin/bash
# CDC Pipeline Setup Script
# This script sets up and starts the entire CDC pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    print_info "Docker is installed: $(docker --version)"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed or not available as 'docker compose'."
        print_error "Please install Docker Compose v2 or ensure Docker Desktop is updated."
        exit 1
    fi
    print_info "Docker Compose is installed: $(docker compose version)"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_warn ".env file not found. Creating from .env.example..."
        cp .env.example .env
        print_warn "Please edit .env file with your Snowflake credentials before continuing."
        read -p "Press Enter after editing .env file..."
    else
        print_info ".env file found"
    fi
}

# Start core services
start_core_services() {
    print_info "Starting core CDC services..."
    docker compose up -d
    print_info "Core services started"
}

# Wait for services to be ready
wait_for_services() {
    print_info "Waiting for services to be ready..."

    # Wait for PostgreSQL
    print_info "Waiting for PostgreSQL..."
    until docker exec postgres pg_isready -U postgres &> /dev/null; do
        sleep 2
    done
    print_info "PostgreSQL is ready"

    # Wait for Kafka
    print_info "Waiting for Kafka..."
    sleep 10
    until docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list &> /dev/null; do
        sleep 2
    done
    print_info "Kafka is ready"

    # Wait for Schema Registry
    print_info "Waiting for Schema Registry..."
    until curl -s http://localhost:8081/ &> /dev/null; do
        sleep 2
    done
    print_info "Schema Registry is ready"

    # Wait for Kafka Connect (with timeout)
    print_info "Waiting for Kafka Connect..."
    CONNECT_TIMEOUT=30
    CONNECT_ELAPSED=0
    until curl -s http://localhost:8083/ &> /dev/null; do
        sleep 2
        CONNECT_ELAPSED=$((CONNECT_ELAPSED + 2))
        if [ $CONNECT_ELAPSED -ge $CONNECT_TIMEOUT ]; then
            print_warn "Kafka Connect did not start within ${CONNECT_TIMEOUT}s - skipping (optional for LinkedIn ingestion)"
            return 0
        fi
    done
    print_info "Kafka Connect is ready"
}

# Deploy Debezium connector
deploy_connector() {
    print_info "Deploying Debezium connector..."
    cd connectors
    ./deploy-connector.sh
    cd ..
    print_info "Debezium connector deployed"
}

# Start monitoring stack
start_monitoring() {
    print_info "Starting monitoring stack..."
    docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
    print_info "Monitoring stack started"
}

# Display access information
display_info() {
    echo ""
    echo "=========================================="
    echo "CDC Pipeline Setup Complete!"
    echo "=========================================="
    echo ""
    echo "Access Points:"
    echo "  - Kafka UI:        http://localhost:8080"
    echo "  - Kafka Connect:   http://localhost:8083"
    echo "  - Schema Registry: http://localhost:8081"
    echo "  - Grafana:         http://localhost:3001 (admin/admin)"
    echo "  - Prometheus:      http://localhost:9090"
    echo "  - AlertManager:    http://localhost:9093"
    echo ""
    echo "PostgreSQL:"
    echo "  - Host: localhost:5432"
    echo "  - Database: sourcedb"
    echo "  - User: postgres"
    echo "  - Password: postgres"
    echo ""
    echo "Useful Commands:"
    echo "  - View logs:           docker compose logs -f"
    echo "  - Check connector:     ./connectors/check-connector.sh"
    echo "  - Test consumer:       cd consumer && python local_test_consumer.py"
    echo "  - Shutdown:            ./shutdown.sh"
    echo "  - Full teardown:       ./teardown.sh"
    echo ""
}

# Main execution
main() {
    echo "=========================================="
    echo "CDC Pipeline Setup"
    echo "=========================================="
    echo ""

    # Check prerequisites
    check_docker
    check_docker_compose
    check_env_file

    # Setup pipeline
    start_core_services
    wait_for_services

    # Only deploy connector if Connect is running
    if curl -s http://localhost:8083/ &> /dev/null; then
        deploy_connector
    else
        print_warn "Skipping connector deployment (Kafka Connect not available)"
    fi

    # Ask about monitoring
    read -p "Do you want to start the monitoring stack? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_monitoring
    fi

    # Display information
    display_info
}

# Run main function
main
