# CDC Consumer

This directory contains the Python consumer application that reads CDC events from Kafka and loads them into Snowflake.

## Features

- **JSON Message Support**: Reads JSON-encoded CDC messages from Kafka
- **Batch Processing**: Configurable batch sizes for efficient loading
- **Operation Support**: Handles INSERT, UPDATE, and DELETE operations correctly
- **Error Handling**: Comprehensive error handling with validation
- **Idempotent Writes**: Uses proper UPDATE statements to prevent duplicates
- **Auto Schema Management**: Automatically creates tables if they don't exist
- **Graceful Shutdown**: Handles signals and flushes buffers on shutdown
- **Primary Key Detection**: Smart primary key detection with fallback patterns

## Files

- `cdc_consumer.py` - Main consumer for Snowflake integration
- `local_test_consumer.py` - Test consumer for local development (no Snowflake required)
- `requirements.txt` - Python dependencies
- `Dockerfile` - Container image definition
- `README.md` - This file

## Configuration

The consumer is configured via environment variables:

### Kafka Configuration
```bash
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
SCHEMA_REGISTRY_URL=http://localhost:8081
CONSUMER_GROUP_ID=cdc-consumer-group
```

### Snowflake Configuration
```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=CDC_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

### Consumer Configuration
```bash
BATCH_SIZE=100              # Number of messages to batch before writing
POLL_TIMEOUT=1.0            # Kafka poll timeout in seconds
LOG_LEVEL=INFO              # Logging level (DEBUG, INFO, WARNING, ERROR)
```

## Local Testing (Without Snowflake)

For testing without Snowflake, use the local test consumer:

```bash
# Install dependencies
pip install -r requirements.txt

# Run test consumer
python local_test_consumer.py
```

The test consumer will:
- Connect to Kafka and Schema Registry
- Subscribe to CDC topics
- Print formatted CDC messages to console
- Show operation type, before/after states, and metadata

Example output:
```
================================================================================
Operation: UPDATE
Table: customers
Timestamp: 1234567890
LSN: 67890

Before: {
  "customer_id": 1,
  "email": "old@example.com",
  "first_name": "John"
}

After: {
  "customer_id": 1,
  "email": "new@example.com",
  "first_name": "John"
}
================================================================================
```

## Running with Snowflake

### Using Docker Compose

The consumer is already configured in `docker compose.yml`:

```bash
# Start the entire stack
docker compose up -d

# View consumer logs
docker compose logs -f cdc-consumer
```

### Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export SCHEMA_REGISTRY_URL=http://localhost:8081
export SNOWFLAKE_ACCOUNT=your_account
export SNOWFLAKE_USER=your_username
export SNOWFLAKE_PASSWORD=your_password

# Run consumer
python cdc_consumer.py
```

## How It Works

### 1. Message Consumption
- Consumer subscribes to CDC topics (e.g., `cdc.customers`, `cdc.products`)
- Polls Kafka for new messages with configurable timeout
- Deserializes Avro messages using Schema Registry

### 2. Buffering
- Messages are buffered per table
- When buffer reaches `BATCH_SIZE`, it's flushed to Snowflake
- Buffers are also flushed on timeout or shutdown

### 3. Table Management
- On first message for a table, checks if table exists in Snowflake
- If not, creates table with inferred schema
- Adds CDC metadata columns:
  - `_cdc_operation`: Operation type (c, u, d, r)
  - `_cdc_timestamp`: CDC event timestamp
  - `_cdc_source_lsn`: PostgreSQL LSN (Log Sequence Number)
  - `_cdc_processed_at`: Consumer processing timestamp

### 4. Operation Handling

#### INSERT (operations: 'c' create, 'r' read/snapshot)
```sql
MERGE INTO table AS target
USING (SELECT values) AS source
ON FALSE
WHEN NOT MATCHED THEN INSERT (columns) VALUES (values)
```

#### UPDATE (operation: 'u')
```sql
UPDATE table
SET col1 = val1, col2 = val2, ...,
    _cdc_operation = 'u',
    _cdc_timestamp = timestamp,
    _cdc_source_lsn = lsn
WHERE primary_key = value
```

**Note**: The UPDATE operation correctly uses the primary key from the `after` data to ensure rows are matched properly. The consumer validates primary key existence and logs warnings when updates match zero rows.

#### DELETE (operation: 'd')
```sql
DELETE FROM table
WHERE primary_key = value
```

### 5. Error Handling
- Serialization errors are logged and skipped
- Database errors roll back the transaction
- Uncommitted messages are reprocessed on restart
- Fatal errors trigger graceful shutdown

## Schema Evolution

The consumer handles schema changes automatically:

### Adding Columns
- New columns in CDC events are added to Snowflake table
- Existing rows get NULL values for new columns

### Removing Columns
- Removed columns in CDC events are ignored
- Data in Snowflake is preserved

### Type Changes
- Type inference happens on table creation
- Subsequent changes may require manual intervention
- Use Snowflake VARIANT type for flexibility

## Performance Tuning

### High Throughput
```bash
BATCH_SIZE=1000
POLL_TIMEOUT=5.0
```

### Low Latency
```bash
BATCH_SIZE=10
POLL_TIMEOUT=0.1
```

### Memory Optimization
```bash
BATCH_SIZE=100
# Add consumer config:
fetch.min.bytes=1048576      # Wait for 1MB before fetch
max.partition.fetch.bytes=1048576
```

## Monitoring

The consumer logs key metrics:
- Messages processed per batch
- Batch write times
- Errors and exceptions
- Connection status

Example log output:
```
2024-01-15 10:30:45 - INFO - Connected to Snowflake successfully
2024-01-15 10:30:46 - INFO - Subscribed to topics: ['cdc.customers', ...]
2024-01-15 10:30:47 - INFO - Batch written to customers: 50 inserts, 10 updates, 2 deletes
```

## Troubleshooting

### Consumer not receiving messages
1. Check Kafka connection: `docker logs kafka`
2. Verify topics exist: `docker exec kafka kafka-topics --list --bootstrap-server localhost:29092`
3. Check consumer group lag: `docker exec kafka kafka-consumer-groups --bootstrap-server localhost:29092 --describe --group cdc-consumer-group`

### Schema Registry errors
1. Verify Schema Registry is running: `curl http://localhost:8081`
2. Check registered schemas: `curl http://localhost:8081/subjects`
3. Ensure Avro schemas are compatible

### Snowflake connection issues
1. Verify credentials and account identifier
2. Check network connectivity to Snowflake
3. Ensure warehouse is running and accessible
4. Verify user has proper permissions (CREATE TABLE, INSERT, UPDATE, DELETE)

### Table creation failures
1. Check user has CREATE TABLE permission
2. Verify schema exists in Snowflake
3. Review type inference logic for edge cases

### Lag and performance issues
1. Increase `BATCH_SIZE` for higher throughput
2. Ensure Snowflake warehouse is appropriately sized
3. Monitor Kafka consumer lag
4. Consider adding more consumer instances (scale horizontally)

## Development

### Running Tests
```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/

# Run with coverage
pytest --cov=cdc_consumer tests/
```

### Adding Custom Transformations
Extend the `process_message` method to add custom logic:

```python
def process_message(self, message):
    value = message.value()

    # Custom transformation
    if value.get('op') == 'u':
        # Log significant updates
        if value['after']['price'] != value['before']['price']:
            logger.warning(f"Price changed: {value['before']['price']} -> {value['after']['price']}")

    # Continue with normal processing
    super().process_message(message)
```

### Dead Letter Queue
For production use, consider adding a DLQ for failed messages:

```python
def _handle_failed_message(self, message, error):
    """Send failed messages to DLQ"""
    dlq_topic = f"dlq.{message.topic()}"
    self.producer.produce(dlq_topic, value=message.value())
    logger.error(f"Message sent to DLQ: {error}")
```

## Security Best Practices

1. **Never commit credentials**: Use environment variables or secrets management
2. **Use Snowflake key pair authentication**: More secure than password
3. **Enable SSL/TLS**: For Kafka and Snowflake connections
4. **Rotate credentials regularly**: Update passwords/keys periodically
5. **Limit permissions**: Grant only necessary privileges
6. **Encrypt sensitive logs**: Redact credentials in log output

## Future Enhancements

- [ ] Add Prometheus metrics endpoint
- [ ] Implement dead letter queue
- [ ] Support for schema registry authentication
- [ ] Configurable retry logic with exponential backoff
- [ ] Support for multiple Snowflake warehouses
- [ ] CDC metadata enrichment
- [ ] Support for other targets (BigQuery, Redshift, etc.)
