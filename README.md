# CDC Pipeline with Debezium, Kafka, and Snowflake

A production-ready Change Data Capture (CDC) pipeline that ingests data from external APIs (LinkedIn Jobs via RapidAPI), stores it in PostgreSQL, captures changes using Debezium, streams them through Kafka, and loads them into Snowflake for analytics.

## Features

- **API Data Ingestion**: Automated fetching from RapidAPI JSearch LinkedIn API
- **Real-time CDC**: Capture database changes with sub-second latency
- **Scalable Architecture**: Built on Kafka for horizontal scalability
- **Schema Evolution**: Automatic schema management and evolution
- **Monitoring & Observability**: Comprehensive monitoring with Prometheus, Grafana, and Loki
- **Error Handling**: Robust error handling and retry mechanisms
- **Local Development**: Docker-based setup for easy local testing
- **Production Ready**: Includes best practices for production deployment
- **Complete CDC Support**: Handles INSERT, UPDATE, and DELETE operations correctly

## Architecture

```
RapidAPI JSearch LinkedIn
    ↓
API Ingestion Service
    ↓
PostgreSQL (Source DB)
    ↓
Debezium Connector (CDC)
    ↓
Kafka + Schema Registry (Streaming)
    ↓
Python Consumer
    ↓
Snowflake (Data Warehouse)
```

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM minimum (16GB recommended)
- 20GB free disk space

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd cdc-pipeline

# Run setup script
./setup.sh
```

The setup script will:
- Check prerequisites
- Create `.env` file from template (if needed)
- Start all services
- Deploy Debezium connector
- Optionally start monitoring stack

### 2. Configure RapidAPI (Required)

Get your RapidAPI key and configure the LinkedIn job ingestion:

1. Sign up at https://rapidapi.com
2. Subscribe to JSearch LinkedIn API: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
3. Edit `.env` with your API key:

```bash
RAPIDAPI_KEY=your_rapidapi_key_here

# Optional: Customize search parameters
SEARCH_QUERIES=software engineer,data engineer,python developer
SEARCH_LOCATION=United States
SCHEDULE_INTERVAL_MINUTES=60
```

### 3. Configure Snowflake (Optional)

If you want to load data into Snowflake, edit `.env` with your credentials.

**Option A: Password Authentication** (not recommended for production)

```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=CDC_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

**Option B: Private Key Authentication** (recommended)

```bash
SNOWFLAKE_ACCOUNT=your_account
SNOWFLAKE_USER=your_username
# Path to your existing private key (e.g., in ~/.ssh/)
SNOWFLAKE_PRIVATE_KEY_HOST_PATH=/Users/your_username/.ssh/snowflake_key.p8
SNOWFLAKE_PRIVATE_KEY_PATH=/app/keys/snowflake_key.p8
SNOWFLAKE_PRIVATE_KEY_PASSPHRASE=
SNOWFLAKE_DATABASE=CDC_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
```

Note: The private key should already exist on your system (e.g., in your `~/.ssh/` directory). No need to copy it to the repo.

### 4. Test Locally (Without Snowflake)

```bash
# Install Python dependencies
cd consumer
pip install -r requirements.txt

# Run local test consumer
python local_test_consumer.py
```

### 5. View Ingested LinkedIn Jobs

The API ingestion service automatically fetches LinkedIn jobs. View them in PostgreSQL:

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d sourcedb

# View recent jobs
SELECT job_id, job_title, company_name, location, posted_date
FROM linkedin_jobs
ORDER BY first_seen_at DESC
LIMIT 10;

# View jobs by company
SELECT company_name, COUNT(*) as job_count
FROM linkedin_jobs
GROUP BY company_name
ORDER BY job_count DESC;
```

### 6. Generate Additional Test Data

You can also insert test data into the sample tables:

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d sourcedb

# Insert test data
INSERT INTO customers (email, first_name, last_name, phone, city, state)
VALUES ('test@example.com', 'Test', 'User', '555-0199', 'Seattle', 'WA');

# Update data
UPDATE customers SET city = 'Portland' WHERE email = 'test@example.com';

# Delete data
DELETE FROM customers WHERE email = 'test@example.com';
```

Watch the changes flow through the pipeline in real-time!

## Project Structure

```
cdc-pipeline/
├── ARCHITECTURE.md              # Detailed architecture documentation
├── README.md                    # This file
├── docker-compose.yml           # Core services configuration
├── docker-compose.monitoring.yml # Monitoring stack
├── setup.sh                     # Automated setup script
├── shutdown.sh                  # Graceful shutdown script
├── .env.example                 # Environment variables template
│
├── api-ingestion/               # LinkedIn API data ingestion
│   ├── linkedin_ingestion.py   # API ingestion service
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Container image
│   └── README.md               # API ingestion documentation
│
├── init-scripts/                # PostgreSQL initialization
│   ├── 01-create-schema.sql    # Database schema
│   ├── 02-sample-data.sql      # Sample data
│   └── 03-create-replication-user.sql
│
├── connectors/                  # Debezium connector configuration
│   ├── postgres-connector.json # Connector config
│   ├── deploy-connector.sh     # Deployment script
│   ├── check-connector.sh      # Status check script
│   └── README.md               # Connector documentation
│
├── consumer/                    # Python CDC consumer
│   ├── cdc_consumer.py         # Main consumer (Snowflake)
│   ├── local_test_consumer.py  # Test consumer (no Snowflake)
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Container image
│   └── README.md               # Consumer documentation
│
└── monitoring/                  # Monitoring configuration
    ├── prometheus/             # Metrics collection
    ├── grafana/                # Dashboards
    ├── loki/                   # Log aggregation
    ├── promtail/               # Log shipping
    ├── jmx-exporter/           # Kafka metrics
    ├── alertmanager/           # Alert routing
    └── README.md               # Monitoring documentation
```

## Access Points

After running `./setup.sh`, access the following UIs:

| Service | URL | Credentials |
|---------|-----|-------------|
| Kafka UI | http://localhost:8080 | - |
| Kafka Connect | http://localhost:8083 | - |
| Schema Registry | http://localhost:8081 | - |
| Grafana | http://localhost:3001 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| AlertManager | http://localhost:9093 | - |

## Common Tasks

### Check Service Status

```bash
# All services
docker-compose ps

# Specific service
docker-compose logs -f kafka
docker-compose logs -f connect
docker-compose logs -f postgres
```

### Check Connector Status

```bash
./connectors/check-connector.sh
```

### View Kafka Topics

```bash
# List all topics
docker exec kafka kafka-topics --bootstrap-server localhost:29092 --list

# View messages in a topic
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic cdc.customers \
  --from-beginning
```

### Test CDC Events

```bash
# Connect to PostgreSQL
docker exec -it postgres psql -U postgres -d sourcedb

# Make changes
UPDATE products SET price = price * 1.1 WHERE category = 'Electronics';
```

### View Consumer Logs

```bash
# Snowflake consumer
docker-compose logs -f cdc-consumer

# Local test consumer
cd consumer && python local_test_consumer.py
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart connect
docker-compose restart cdc-consumer
```

## Monitoring and Observability

### Start Monitoring Stack

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

### Access Grafana

1. Open http://localhost:3001
2. Login with admin / admin
3. Navigate to Dashboards → CDC Pipeline Overview

### View Logs in Loki

1. Open Grafana
2. Go to Explore
3. Select Loki datasource
4. Query: `{container_name="cdc-consumer"}`

### Check Metrics in Prometheus

1. Open http://localhost:9090
2. Query examples:
   - `up` - Service health
   - `kafka_server_brokertopicmetrics_messagesinpersec_count` - Message rate
   - `kafka_consumergroup_lag` - Consumer lag

For detailed monitoring documentation, see [monitoring/README.md](monitoring/README.md).

## Troubleshooting

### Services Won't Start

```bash
# Check Docker resources
docker system info

# Check disk space
df -h

# View service logs
docker-compose logs
```

### Connector Failed

```bash
# Check connector status
curl http://localhost:8083/connectors/postgres-cdc-connector/status | jq '.'

# Restart connector
curl -X POST http://localhost:8083/connectors/postgres-cdc-connector/restart

# View Connect logs
docker-compose logs connect
```

### No Messages in Kafka

```bash
# Check Debezium connector tasks
curl http://localhost:8083/connectors/postgres-cdc-connector/status

# Check PostgreSQL replication slot
docker exec postgres psql -U postgres -d sourcedb -c "SELECT * FROM pg_replication_slots;"

# Check PostgreSQL logs
docker-compose logs postgres
```

### Consumer Not Processing Messages

```bash
# Check consumer logs
docker-compose logs cdc-consumer

# Check consumer group lag
docker exec kafka kafka-consumer-groups \
  --bootstrap-server localhost:29092 \
  --describe \
  --group cdc-consumer-group

# Restart consumer
docker-compose restart cdc-consumer
```

### High Consumer Lag

1. Increase batch size in `.env`:
   ```bash
   BATCH_SIZE=1000
   ```

2. Scale consumer horizontally (add more instances)

3. Check Snowflake warehouse size

4. Monitor system resources

## Performance Tuning

### For High Throughput

```bash
# Connector configuration
max.batch.size=4096
max.queue.size=16384

# Consumer configuration
BATCH_SIZE=1000
POLL_TIMEOUT=5.0

# Kafka configuration
batch.size=65536
linger.ms=100
compression.type=lz4
```

### For Low Latency

```bash
# Connector configuration
max.batch.size=512
poll.interval.ms=100

# Consumer configuration
BATCH_SIZE=10
POLL_TIMEOUT=0.1
```

## Production Deployment

### Kubernetes Deployment

For production deployment on Kubernetes:

1. Use managed Kafka service (MSK, Confluent Cloud)
2. Deploy Kafka Connect with multiple workers
3. Use Kubernetes StatefulSets for stateful services
4. Configure resource limits and requests
5. Implement pod disruption budgets
6. Use persistent volumes for data
7. Enable TLS/SSL for all connections

### Security Best Practices

## 🔒 Security

### Development vs Production Credentials

This project includes **development credentials** for local Docker environments. These are safe for local development but **MUST be changed for production deployments**.

#### Development Credentials (Local Use Only)

The following credentials are configured for local development:

| Service | Username | Password | Location |
|---------|----------|----------|----------|
| PostgreSQL | `postgres` | `postgres` | [docker-compose.yml](docker-compose.yml) |
| Debezium User | `debezium` | `debezium_password` | [init-scripts/03-create-replication-user.sh](init-scripts/03-create-replication-user.sh) |
| Grafana Admin | `admin` | `admin` | [docker-compose.monitoring.yml](docker-compose.monitoring.yml) |

**⚠️ WARNING**: These credentials are:
- Only for local Docker development
- NOT suitable for production
- Must be changed via environment variables for any non-local deployment

#### Changing Credentials

All credentials can be changed via the `.env` file:

```bash
# PostgreSQL Configuration
POSTGRES_USER=your_secure_username
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=sourcedb

# Debezium Replication User
DEBEZIUM_USER=your_debezium_user
DEBEZIUM_PASSWORD=your_secure_debezium_password

# Grafana Admin
GRAFANA_ADMIN_USER=your_admin_username
GRAFANA_ADMIN_PASSWORD=your_secure_admin_password
```

### Security Checklist for Production

- [ ] Change all default passwords in `.env` file
- [ ] Use Snowflake private key authentication instead of password
- [ ] Enable TLS/SSL for all connections (Kafka, PostgreSQL, Snowflake)
- [ ] Use secrets management system (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Implement network isolation (VPCs, security groups, firewalls)
- [ ] Enable Kafka authentication and authorization (SASL/ACLs)
- [ ] Configure PostgreSQL SSL and strong authentication
- [ ] Use Snowflake role-based access control (RBAC)
- [ ] Enable audit logging on all systems
- [ ] Implement data encryption at rest
- [ ] Rotate credentials regularly (90 days recommended)
- [ ] Use strong passwords (16+ characters, mixed case, numbers, symbols)
- [ ] Never commit `.env` file or private keys to version control
- [ ] Implement IP whitelisting where possible
- [ ] Enable monitoring and alerting for security events

### Sensitive Files Protection

The repository is configured to ignore sensitive files:

```gitignore
# Environment variables with credentials
.env

# Snowflake private keys and certificates (if accidentally copied to repo)
keys/
*.p8
*.pem
*.key
*.crt

# Generated connector configurations (may contain credentials)
connectors/postgres-connector.json
```

**Important**:

- Store your Snowflake private keys in your system's SSH directory (e.g., `~/.ssh/snowflake_key.p8`)
- Never copy private keys into the repository directory
- The `.env` file should only reference the path to your existing key
- The repository's `keys/` directory is ignored to prevent accidental commits, but you shouldn't use it

**Always verify** before committing:

```bash
git status --ignored
```

### Credentials Management Best Practices

1. **Use Environment Variables**
   - Never hardcode credentials in source code
   - Use `.env` file for local development
   - Use secrets management systems for production

2. **Secrets Management Systems**
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Cloud Secret Manager
   - Kubernetes Secrets

3. **Rotate Credentials Regularly**
   - Database passwords: Every 90 days
   - API keys: Every 180 days
   - Snowflake private keys: Annually
   - Service account credentials: When team members leave

4. **Access Control**
   - Use principle of least privilege
   - Enable Kafka ACLs for topic-level security
   - Configure PostgreSQL row-level security if needed
   - Use Snowflake role-based access control
   - Implement MFA for admin accounts

5. **Data Protection**
   - Enable encryption at rest and in transit
   - Implement data masking for PII/sensitive fields
   - Configure audit logging for compliance
   - Use Snowflake data classification tags

### Network Security

For production deployments:

1. **TLS/SSL Configuration**
   ```bash
   # Kafka
   security.protocol=SSL
   ssl.truststore.location=/path/to/truststore.jks

   # PostgreSQL
   sslmode=require

   # Snowflake (automatic with private key auth)
   ```

2. **Firewall Rules**
   - Restrict PostgreSQL access to Debezium connector only
   - Limit Kafka access to authorized consumers/producers
   - Use VPC peering for Snowflake connectivity

3. **Network Segmentation**
   - Separate networks for different components
   - Use private subnets for databases
   - Implement bastion hosts for administrative access

### High Availability

1. **Kafka**: 3+ brokers with replication factor 3
2. **Zookeeper**: 3+ nodes for quorum
3. **Kafka Connect**: Multiple workers in distributed mode
4. **PostgreSQL**: Primary-replica setup
5. **Consumer**: Multiple instances for load distribution

### Monitoring in Production

1. Set up alerting for:
   - Service downtime
   - High consumer lag
   - Connector failures
   - Resource exhaustion

2. Configure log aggregation and retention

3. Implement distributed tracing

4. Set up on-call rotation and runbooks

## Scaling

### Horizontal Scaling

```bash
# Scale Kafka consumers
docker-compose up -d --scale cdc-consumer=3

# Add Kafka brokers (modify docker-compose.yml)
# Add Connect workers (modify docker-compose.yml)
```

### Vertical Scaling

Adjust resource limits in docker-compose.yml:

```yaml
services:
  kafka:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
```

## Backup and Recovery

### Backup Kafka Topics

```bash
# Backup topic data
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic cdc.customers \
  --from-beginning \
  --max-messages 100000 > backup.json
```

### Backup PostgreSQL

```bash
# Backup database
docker exec postgres pg_dump -U postgres sourcedb > backup.sql

# Restore database
docker exec -i postgres psql -U postgres sourcedb < backup.sql
```

### Backup Configurations

```bash
# Backup connector configuration
curl http://localhost:8083/connectors/postgres-cdc-connector/config > connector-backup.json

# Backup Grafana dashboards
docker exec grafana grafana-cli admin export > grafana-backup.json
```

## Development

### Running Tests

```bash
# Consumer tests
cd consumer
pytest tests/

# Integration tests
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Adding New Tables

1. Create table in PostgreSQL
2. Update `table.include.list` in `connectors/postgres-connector.json`
3. Redeploy connector: `./connectors/deploy-connector.sh`
4. Consumer will auto-create Snowflake table on first message

### Custom Transformations

Edit `cdc_consumer.py` to add custom transformation logic in the `process_message` method.

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- Check [Troubleshooting](#troubleshooting) section
- Review component-specific READMEs
- Open an issue on GitHub

## Resources

- [Debezium Documentation](https://debezium.io/documentation/)
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Snowflake Documentation](https://docs.snowflake.com/)
- [Confluent Schema Registry](https://docs.confluent.io/platform/current/schema-registry/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)

## Acknowledgments

Built with:
- Debezium 2.5
- Apache Kafka 7.5
- PostgreSQL 14
- Python 3.11
- Snowflake Connector
- Prometheus & Grafana

---

**Note**: This pipeline is designed for both development and production use. For production deployments, review and adjust configurations based on your specific requirements for security, performance, and scalability.
