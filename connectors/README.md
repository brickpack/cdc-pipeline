# Debezium Connector Configuration

This directory contains configuration and management scripts for the Debezium PostgreSQL connector.

## Files

- `postgres-connector.json` - Connector configuration
- `deploy-connector.sh` - Script to deploy/update the connector
- `check-connector.sh` - Script to check connector status and health

## Connector Configuration

The PostgreSQL connector is configured with the following key settings:

### Connection Settings
- **Database**: sourcedb on postgres:5432
- **User**: debezium (replication user)
- **Plugin**: pgoutput (native PostgreSQL logical replication)

### Snapshot Behavior
- **Mode**: `initial` - Performs initial snapshot of existing data
- **Locking**: `minimal` - Uses minimal locking during snapshot

### Topic Configuration
- **Prefix**: dbserver
- **Routing**: Transforms topics to `cdc.<table_name>` format
- **Tables**: customers, products, orders, order_items, inventory_transactions

### Data Formats
- **Key/Value Converter**: JSON (JsonConverter)
- **Schema Registry**: Available but not required for JSON format
- **Decimal Handling**: Converted to double
- **Tombstones**: Enabled for delete events

### Performance Tuning
- **Max Batch Size**: 2048 records
- **Max Queue Size**: 8192 records
- **Poll Interval**: 1000ms

### Monitoring
- **Heartbeat**: Every 10 seconds
- **Transaction Metadata**: Enabled
- **Error Logging**: Full logging enabled

## Deployment

### Deploy the Connector

```bash
cd connectors
./deploy-connector.sh
```

This script will:
1. Wait for Kafka Connect to be ready
2. Create the connector if it doesn't exist
3. Update the connector configuration if it already exists
4. Display the connector status

### Check Connector Status

```bash
./check-connector.sh
```

This script displays:
- Kafka Connect cluster information
- List of all connectors
- Detailed status of each connector
- Error messages (if any)
- List of created topics
- Sample messages from CDC topics

### Manual Operations

#### List all connectors
```bash
curl http://localhost:8083/connectors
```

#### Get connector status
```bash
curl http://localhost:8083/connectors/postgres-cdc-connector/status | jq '.'
```

#### Delete connector
```bash
curl -X DELETE http://localhost:8083/connectors/postgres-cdc-connector
```

#### Restart connector
```bash
curl -X POST http://localhost:8083/connectors/postgres-cdc-connector/restart
```

#### Get connector configuration
```bash
curl http://localhost:8083/connectors/postgres-cdc-connector/config | jq '.'
```

## Topic Structure

The connector creates the following topics:

### Data Topics
- `cdc.customers` - Customer change events
- `cdc.products` - Product change events
- `cdc.orders` - Order change events
- `cdc.order_items` - Order item change events
- `cdc.inventory_transactions` - Inventory transaction events

### System Topics
- `__debezium-heartbeat.dbserver` - Heartbeat messages
- `dbserver` - Transaction metadata (if enabled)

## Message Format

Each CDC message contains:

### Key
- Primary key fields from the table

### Value
```json
{
  "before": { ... },    // Row state before change (null for INSERT)
  "after": { ... },     // Row state after change (null for DELETE)
  "source": {
    "version": "2.5.0.Final",
    "connector": "postgresql",
    "name": "dbserver",
    "ts_ms": 1234567890,
    "snapshot": "false",
    "db": "sourcedb",
    "schema": "public",
    "table": "customers",
    "txId": 12345,
    "lsn": 67890
  },
  "op": "c",            // Operation: c=create, u=update, d=delete, r=read(snapshot)
  "ts_ms": 1234567890,  // Timestamp
  "transaction": null
}
```

## Troubleshooting

### Connector fails to start
1. Check PostgreSQL is accessible: `docker exec postgres pg_isready`
2. Verify replication user exists: `docker exec postgres psql -U postgres -c "\du"`
3. Check publication exists: `docker exec postgres psql -U postgres -d sourcedb -c "\dRp"`
4. Review connector logs: `docker logs connect`

### No messages in topics
1. Verify connector is running: `./check-connector.sh`
2. Check replication slot: `docker exec postgres psql -U postgres -d sourcedb -c "SELECT * FROM pg_replication_slots;"`
3. Perform a database change to trigger CDC event
4. Check Kafka topics: `docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list`

### Connector lag increasing
1. Increase `max.batch.size` for higher throughput
2. Add more tasks: increase `tasks.max`
3. Check network latency between components
4. Monitor Kafka broker performance

### Schema evolution issues
1. Ensure Schema Registry is accessible
2. Check schema compatibility mode: `backward` allows adding fields
3. Review schema versions: `curl http://localhost:8081/subjects`
4. Test schema changes in development first

## Performance Optimization

### High Throughput
```json
{
  "max.batch.size": "4096",
  "max.queue.size": "16384",
  "tasks.max": "2"
}
```

### Low Latency
```json
{
  "max.batch.size": "512",
  "poll.interval.ms": "100",
  "max.queue.size": "2048"
}
```

### Large Snapshots
```json
{
  "snapshot.fetch.size": "10000",
  "snapshot.max.threads": "4"
}
```

## Configuration Reference

See the [Debezium PostgreSQL Connector Documentation](https://debezium.io/documentation/reference/stable/connectors/postgresql.html) for complete configuration options.
