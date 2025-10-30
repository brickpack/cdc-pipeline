# CDC Pipeline Architecture

## Overview

This CDC (Change Data Capture) pipeline captures real-time changes from PostgreSQL databases using Debezium, streams them through Kafka, and loads them into Snowflake for analytics.

## Architecture Components

```
┌─────────────────┐
│   PostgreSQL    │
│  Source Database│
└────────┬────────┘
         │ WAL
         ↓
┌─────────────────┐
│    Debezium     │
│    Connector    │
└────────┬────────┘
         │ CDC Events
         ↓
┌─────────────────┐
│  Kafka Cluster  │
│  + Zookeeper    │
│  + Schema Reg.  │
└────────┬────────┘
         │ Stream
         ↓
┌─────────────────┐
│  CDC Consumer   │
│   (Python)      │
└────────┬────────┘
         │ Batch Load
         ↓
┌─────────────────┐
│   Snowflake     │
│  Data Warehouse │
└─────────────────┘

    Monitoring Stack:
    ┌──────────────┐
    │  Prometheus  │
    │   Grafana    │
    │     Loki     │
    └──────────────┘
```

## Data Flow

### 1. Change Capture
- PostgreSQL writes all changes to Write-Ahead Log (WAL)
- Debezium connector reads WAL using logical decoding
- Captures INSERT, UPDATE, DELETE operations with full row data
- Publishes changes to Kafka topics (one topic per table by default)

### 2. Event Streaming
- Kafka brokers store CDC events durably
- Schema Registry stores Avro schemas for data validation
- Events include before/after state, operation type, and metadata
- Kafka guarantees ordering within partitions

### 3. Data Loading
- Python consumer reads from Kafka topics
- Transforms CDC events into warehouse-compatible format
- Handles schema evolution and data type mapping
- Batches inserts for efficiency
- Implements retry logic and error handling

### 4. Monitoring & Observability
- Prometheus scrapes metrics from all components
- Grafana visualizes pipeline health and throughput
- Loki aggregates logs for troubleshooting
- Alerts on lag, errors, and performance degradation

## Component Details

### PostgreSQL Source
- **Version**: 14+ (with logical replication support)
- **Configuration**:
  - `wal_level = logical`
  - `max_replication_slots >= 1`
  - Replication user with appropriate permissions
- **Schema**: Sample tables for testing (customers, orders, products)

### Debezium Connector
- **Type**: Debezium PostgreSQL Connector
- **Deployment**: Kafka Connect in distributed mode
- **Features**:
  - Snapshot mode for initial data load
  - Incremental streaming of changes
  - Heartbeat monitoring
  - Schema change detection

### Kafka Infrastructure
- **Zookeeper**: Cluster coordination (1 node for dev, 3+ for prod)
- **Kafka Broker**: Message broker (1 node for dev, 3+ for prod)
- **Schema Registry**: Confluent Schema Registry for Avro schemas
- **Topics**: Auto-created per table (e.g., `dbserver.public.customers`)

### CDC Consumer
- **Language**: Python 3.9+
- **Libraries**:
  - `confluent-kafka` - Kafka client
  - `snowflake-connector-python` - Snowflake connection
  - `avro-python3` - Avro deserialization
- **Features**:
  - Configurable batch sizes
  - Dead letter queue for failed records
  - Idempotent writes
  - Schema mapping

### Monitoring Stack
- **Prometheus**: Metrics collection and storage
- **Grafana**: Dashboards for visualization
- **Loki**: Log aggregation and querying
- **Exporters**: JMX exporter for Kafka/Connect metrics

## Deployment Options

### Docker Compose (Development)
- Single-node deployment
- All services on one host
- Suitable for local testing
- Fast startup and teardown

### Kubernetes (Production)
- Multi-node deployment
- High availability and scalability
- Resource isolation
- Rolling updates

## Scaling Considerations

### Horizontal Scaling
- **Kafka**: Add more brokers and increase partition count
- **Consumers**: Add consumer instances (up to partition count)
- **Connect**: Scale connector tasks for parallel processing

### Vertical Scaling
- Increase memory for Kafka brokers (page cache)
- More CPU for Connect workers (transformation workload)
- Database connections for consumer (parallel writes)

## Schema Evolution Strategy

### Supported Changes
- **Adding columns**: Backward compatible, null or default values
- **Removing columns**: Consumer ignores unknown fields
- **Type changes**: Handled case-by-case with transformations

### Best Practices
- Use Avro schema evolution features
- Version schemas in Schema Registry
- Test schema changes in staging environment
- Implement consumer fallback logic

## Error Handling

### Connector Failures
- Automatic restart with backoff
- Preserve offset in Kafka
- Alert on repeated failures

### Consumer Failures
- Retry with exponential backoff
- Dead letter queue for poison pills
- Manual intervention for data quality issues

### Network Issues
- Kafka consumer auto-reconnect
- Snowflake connector retry logic
- Circuit breaker pattern for downstream failures

## Security Considerations

### Authentication
- PostgreSQL: Password-based or certificate authentication
- Kafka: SASL/SCRAM or mTLS
- Snowflake: Key pair authentication recommended

### Encryption
- In-transit: TLS for all connections
- At-rest: PostgreSQL encryption, Kafka encryption
- Credentials: Environment variables or secrets management

### Access Control
- Principle of least privilege
- Separate users for each component
- Network segmentation

## Performance Tuning

### Debezium Connector
- `max.batch.size`: Control throughput vs latency
- `max.queue.size`: Buffer size for high-volume changes
- `snapshot.fetch.size`: Rows per snapshot query

### Kafka
- `batch.size`: Producer batching for efficiency
- `linger.ms`: Wait time for batching
- `compression.type`: Reduce network usage (snappy/lz4)

### Consumer
- `max.poll.records`: Records per poll
- `fetch.min.bytes`: Minimum data before fetch returns
- Batch size for Snowflake inserts

## Cost Optimization

### Development
- Use small instance sizes
- Single replicas
- Minimal retention periods

### Production
- Right-size based on load
- Use tiered storage for Kafka
- Snowflake: Auto-suspend, clustering, partitioning

## Next Steps

1. **Phase 1**: Set up local Docker environment
2. **Phase 2**: Deploy PostgreSQL with sample data
3. **Phase 3**: Configure Debezium connector
4. **Phase 4**: Implement and test consumer
5. **Phase 5**: Add monitoring and alerting
6. **Phase 6**: Load testing and optimization
7. **Phase 7**: Production deployment planning
