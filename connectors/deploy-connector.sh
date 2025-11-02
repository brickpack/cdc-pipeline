#!/bin/bash
# Deploy Debezium PostgreSQL connector to Kafka Connect

set -e

CONNECT_HOST="${CONNECT_HOST:-localhost}"
CONNECT_PORT="${CONNECT_PORT:-8083}"
CONNECTOR_TEMPLATE="postgres-connector.template.json"
CONNECTOR_CONFIG="postgres-connector.json"

# Load environment variables from .env if it exists
if [ -f ../.env ]; then
    set -a
    source ../.env
    set +a
fi

# Set defaults for environment variables
export DEBEZIUM_USER="${DEBEZIUM_USER:-debezium}"
export DEBEZIUM_PASSWORD="${DEBEZIUM_PASSWORD:-debezium_password}"
export POSTGRES_DB="${POSTGRES_DB:-sourcedb}"

# Generate connector config from template
echo "Generating connector configuration from template..."
envsubst < "$CONNECTOR_TEMPLATE" > "$CONNECTOR_CONFIG"
echo "✓ Configuration generated"
echo ""

echo "Waiting for Kafka Connect to be ready..."
until curl -f -s "http://${CONNECT_HOST}:${CONNECT_PORT}/" > /dev/null; do
    echo "Kafka Connect is unavailable - waiting..."
    sleep 5
done

echo "Kafka Connect is ready!"
echo ""

# Check if connector already exists
CONNECTOR_NAME=$(cat "$CONNECTOR_CONFIG" | grep -o '"name"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)

if curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors/${CONNECTOR_NAME}" | grep -q "error_code"; then
    echo "Creating new connector: ${CONNECTOR_NAME}"
    curl -X POST \
        -H "Content-Type: application/json" \
        --data @"$CONNECTOR_CONFIG" \
        "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors"
    echo ""
    echo "Connector created successfully!"
else
    echo "Connector ${CONNECTOR_NAME} already exists. Updating configuration..."
    CONNECTOR_CONFIG_ONLY=$(cat "$CONNECTOR_CONFIG" | jq '.config')
    curl -X PUT \
        -H "Content-Type: application/json" \
        --data "$CONNECTOR_CONFIG_ONLY" \
        "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors/${CONNECTOR_NAME}/config"
    echo ""
    echo "Connector updated successfully!"
fi

echo ""
echo "Checking connector status..."
sleep 2
curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors/${CONNECTOR_NAME}/status" | jq '.'

echo ""
echo "Connector deployed! You can check the status at:"
echo "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors/${CONNECTOR_NAME}/status"
