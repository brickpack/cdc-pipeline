# CDC Pipeline Monitoring Stack

Comprehensive monitoring and observability for the CDC pipeline using Prometheus, Grafana, and Loki.

## Components

### Prometheus
- **Port**: 9090
- **Purpose**: Metrics collection and storage
- **Retention**: 30 days
- **Scrape Interval**: 15 seconds

### Grafana
- **Port**: 3000
- **Purpose**: Visualization and dashboards
- **Default Login**: admin / admin
- **Features**: Pre-configured dashboards and datasources

### Loki
- **Port**: 3100
- **Purpose**: Log aggregation
- **Retention**: 31 days
- **Features**: Centralized logging from all services

### Promtail
- **Purpose**: Log collection agent
- **Sources**: Docker containers, application logs

### AlertManager
- **Port**: 9093
- **Purpose**: Alert routing and management
- **Features**: Configurable notification channels

### JMX Exporter
- **Port**: 5556
- **Purpose**: Kafka JMX metrics export
- **Metrics**: Broker, topic, and consumer group metrics

### Node Exporter
- **Port**: 9100
- **Purpose**: System metrics (CPU, memory, disk)

## Quick Start

### Start Monitoring Stack

```bash
# Start main CDC stack first
docker-compose up -d

# Start monitoring stack
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Verify all services are running
docker-compose ps
```

### Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| AlertManager | http://localhost:9093 | - |
| Kafka UI | http://localhost:8080 | - |

### View Logs

```bash
# All monitoring services
docker-compose -f docker-compose.monitoring.yml logs -f

# Specific service
docker-compose logs -f grafana
docker-compose logs -f prometheus
```

## Grafana Setup

### First Login

1. Navigate to http://localhost:3000
2. Login with `admin` / `admin`
3. Change password when prompted (or skip)

### Pre-configured Dashboards

The monitoring stack includes pre-configured dashboards:

1. **CDC Pipeline Overview**
   - Kafka message rates
   - Consumer lag
   - Service health
   - Recent logs

### Creating Custom Dashboards

1. Click "+" → "Dashboard" → "Add new panel"
2. Select "Prometheus" as datasource
3. Enter PromQL query
4. Configure visualization
5. Save dashboard

### Example Queries

#### Kafka Message Rate
```promql
rate(kafka_server_brokertopicmetrics_messagesinpersec_count[5m])
```

#### Consumer Lag
```promql
kafka_consumergroup_lag
```

#### Service Uptime
```promql
up{job="kafka"}
```

#### CPU Usage
```promql
100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## Prometheus Queries

### Access Prometheus UI

Navigate to http://localhost:9090

### Useful Queries

#### Check Service Status
```promql
up
```

#### Kafka Topics
```promql
kafka_server_brokertopicmetrics_messagesinpersec_count
```

#### Disk Space
```promql
(node_filesystem_avail_bytes / node_filesystem_size_bytes) * 100
```

#### Memory Usage
```promql
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100
```

## Loki Log Queries

### Access Logs in Grafana

1. Go to Grafana → Explore
2. Select "Loki" datasource
3. Use LogQL queries

### LogQL Examples

#### All logs from CDC consumer
```logql
{container_name="cdc-consumer"}
```

#### Error logs only
```logql
{container_name="cdc-consumer"} |= "ERROR"
```

#### Logs from last hour with regex filter
```logql
{container_name="cdc-consumer"} |~ "Failed.*" [1h]
```

#### Count errors per minute
```logql
sum(count_over_time({container_name="cdc-consumer"} |= "ERROR" [1m]))
```

## Alerts

### Configured Alerts

The system includes alerts for:

- **Service Health**: Service down detection
- **Kafka**: High lag, offline partitions, under-replicated partitions
- **Kafka Connect**: Connector/task failures
- **System**: High CPU, memory, disk usage
- **PostgreSQL**: Replication lag, inactive slots

### Alert Routing

Alerts are routed based on severity:

- **Critical**: Immediate action required
- **Warning**: Attention needed soon

### Configuring Notifications

Edit `monitoring/alertmanager/alertmanager.yml`:

#### Email Notifications
```yaml
receivers:
  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@example.com'
        from: 'alertmanager@company.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'your-email@gmail.com'
        auth_password: 'your-app-password'
```

#### Slack Notifications
```yaml
receivers:
  - name: 'critical-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#alerts'
        title: 'CRITICAL: {{ .GroupLabels.alertname }}'
```

#### PagerDuty
```yaml
receivers:
  - name: 'critical-alerts'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
```

## Monitoring Best Practices

### 1. Dashboard Organization
- Group related metrics together
- Use consistent color schemes
- Add annotations for deployments
- Set appropriate time ranges

### 2. Alert Configuration
- Set meaningful thresholds
- Avoid alert fatigue
- Use inhibition rules
- Document escalation procedures

### 3. Log Management
- Use structured logging
- Include context in log messages
- Set appropriate log levels
- Implement log rotation

### 4. Retention Policies
- Prometheus: 30 days (configurable)
- Loki: 31 days (configurable)
- Adjust based on storage capacity

### 5. Performance Tuning
- Optimize PromQL queries
- Use recording rules for complex queries
- Configure appropriate scrape intervals
- Monitor monitoring system resource usage

## Troubleshooting

### Prometheus Not Scraping Targets

1. Check target configuration:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

2. Verify service connectivity:
   ```bash
   docker exec prometheus wget -O- http://kafka:9101/metrics
   ```

3. Check Prometheus logs:
   ```bash
   docker-compose logs prometheus
   ```

### Grafana Dashboard Not Loading

1. Verify datasource connection:
   - Grafana → Configuration → Data Sources
   - Click "Test" button

2. Check Grafana logs:
   ```bash
   docker-compose logs grafana
   ```

### Loki Not Receiving Logs

1. Check Promtail status:
   ```bash
   docker-compose logs promtail
   ```

2. Verify Loki API:
   ```bash
   curl http://localhost:3100/ready
   ```

3. Test log ingestion:
   ```bash
   curl -X POST http://localhost:3100/loki/api/v1/push \
     -H "Content-Type: application/json" \
     -d '{"streams":[{"labels":"{job=\"test\"}","entries":[{"ts":"'$(date -u +%Y-%m-%dT%H:%M:%S.%NZ)'","line":"test log"}]}]}'
   ```

### Alerts Not Firing

1. Check alert rules:
   ```bash
   curl http://localhost:9090/api/v1/rules
   ```

2. Verify AlertManager configuration:
   ```bash
   curl http://localhost:9093/api/v2/status
   ```

3. Test alert:
   ```bash
   curl -X POST http://localhost:9093/api/v2/alerts \
     -H "Content-Type: application/json" \
     -d '[{"labels":{"alertname":"test","severity":"warning"},"annotations":{"summary":"Test alert"}}]'
   ```

### High Resource Usage

1. Check container stats:
   ```bash
   docker stats
   ```

2. Optimize Prometheus:
   - Reduce retention period
   - Increase scrape interval
   - Use recording rules

3. Optimize Loki:
   - Adjust retention period
   - Configure compaction
   - Limit ingestion rate

## Maintenance

### Backup Configuration

```bash
# Backup Grafana dashboards
docker exec grafana grafana-cli admin export > grafana-backup.json

# Backup Prometheus data
docker cp prometheus:/prometheus ./prometheus-backup

# Backup alerting rules
cp -r monitoring/ monitoring-backup/
```

### Update Monitoring Stack

```bash
# Pull latest images
docker-compose -f docker-compose.monitoring.yml pull

# Restart services
docker-compose -f docker-compose.monitoring.yml up -d
```

### Clean Up Old Data

```bash
# Remove old Prometheus data
docker exec prometheus promtool tsdb cleanup /prometheus

# Compact Loki data
docker exec loki wget -O- --post-data='' http://localhost:3100/flush
```

## Extending Monitoring

### Add PostgreSQL Metrics

1. Add PostgreSQL exporter to `docker-compose.monitoring.yml`:
```yaml
postgres-exporter:
  image: prometheuscommunity/postgres-exporter
  environment:
    DATA_SOURCE_NAME: "postgresql://postgres:postgres@postgres:5432/sourcedb?sslmode=disable"
  ports:
    - "9187:9187"
```

2. Add scrape config to Prometheus

### Add Custom Metrics

1. Instrument your code:
```python
from prometheus_client import Counter, Histogram, start_http_server

records_processed = Counter('cdc_records_processed', 'CDC records processed')
processing_time = Histogram('cdc_processing_seconds', 'Time spent processing records')
```

2. Expose metrics endpoint
3. Add scrape config to Prometheus

### Create Recording Rules

Edit `prometheus.yml` to add recording rules:
```yaml
groups:
  - name: cdc_recording_rules
    interval: 60s
    rules:
      - record: job:kafka_messages:rate5m
        expr: rate(kafka_server_brokertopicmetrics_messagesinpersec_count[5m])
```

## Security

### Enable Authentication

#### Grafana
- Set strong admin password
- Enable anonymous access control
- Configure OAuth/LDAP

#### Prometheus
- Use basic auth
- Configure TLS
- Restrict network access

#### AlertManager
- Enable authentication
- Configure TLS
- Secure webhook endpoints

### Network Segmentation

Use Docker networks to isolate services:
```yaml
networks:
  monitoring:
    internal: true
  cdc-network:
```

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/)
- [AlertManager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
