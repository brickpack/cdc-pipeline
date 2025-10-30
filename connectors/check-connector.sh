#!/bin/bash
# Check status of Debezium connectors

set -e

CONNECT_HOST="${CONNECT_HOST:-localhost}"
CONNECT_PORT="${CONNECT_PORT:-8083}"

echo "=========================================="
echo "Kafka Connect Cluster Info"
echo "=========================================="
curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/" | jq '.'

echo ""
echo "=========================================="
echo "Installed Connectors"
echo "=========================================="
curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors" | jq '.'

echo ""
echo "=========================================="
echo "Connector Details"
echo "=========================================="

# Get all connectors and check their status
CONNECTORS=$(curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors" | jq -r '.[]')

for connector in $CONNECTORS; do
    echo ""
    echo "Connector: $connector"
    echo "------------------------------------------"

    # Get connector status
    STATUS=$(curl -s "http://${CONNECT_HOST}:${CONNECT_PORT}/connectors/${connector}/status")

    # Parse and display key information
    echo "State: $(echo "$STATUS" | jq -r '.connector.state')"
    echo "Tasks:"
    echo "$STATUS" | jq -r '.tasks[] | "  - Task \(.id): \(.state)"'

    # Check for errors
    if echo "$STATUS" | jq -e '.connector.trace' > /dev/null 2>&1; then
        echo ""
        echo "ERROR DETECTED:"
        echo "$STATUS" | jq -r '.connector.trace'
    fi

    if echo "$STATUS" | jq -e '.tasks[].trace' > /dev/null 2>&1; then
        echo ""
        echo "TASK ERRORS:"
        echo "$STATUS" | jq -r '.tasks[] | select(.trace) | "Task \(.id):\n\(.trace)"'
    fi
done

echo ""
echo "=========================================="
echo "Connector Topics"
echo "=========================================="
echo "Topics created by Debezium:"
docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list | grep -E '^(dbserver|cdc)\.' || echo "No Debezium topics found yet"

echo ""
echo "=========================================="
echo "Recent Messages (Sample)"
echo "=========================================="
TOPICS=$(docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list | grep -E '^cdc\.' | head -1)

if [ -n "$TOPICS" ]; then
    echo "Sampling from topic: $TOPICS"
    docker exec kafka kafka-console-consumer \
        --bootstrap-server localhost:29092 \
        --topic "$TOPICS" \
        --from-beginning \
        --max-messages 1 \
        --timeout-ms 5000 2>/dev/null || echo "No messages yet or timeout reached"
else
    echo "No CDC topics available to sample"
fi
