# LinkedIn Job Data Ingestion Service

This service fetches job data from the RapidAPI JSearch LinkedIn API and stores it in PostgreSQL. Changes in PostgreSQL automatically trigger CDC events through Debezium, which stream to Kafka and eventually load into Snowflake.

## Architecture

```
RapidAPI JSearch LinkedIn
          ↓
  API Ingestion Service
          ↓
     PostgreSQL
          ↓
   Debezium Connector
          ↓
         Kafka
          ↓
     CDC Consumer
          ↓
      Snowflake
```

## Features

- **Scheduled Ingestion**: Runs on a configurable schedule (default: every 60 minutes)
- **Flexible Search**: Configure multiple search queries and locations
- **Upsert Logic**: Automatically updates existing jobs or inserts new ones
- **Error Handling**: Comprehensive error handling and retry logic
- **Rate Limiting**: Built-in delays to respect API rate limits
- **Detailed Logging**: Full audit trail of all ingestion activities
- **CDC Integration**: Seamlessly integrates with existing CDC pipeline

## Getting Started

### Prerequisites

1. **RapidAPI Account**: Sign up at https://rapidapi.com
2. **JSearch API Subscription**: Subscribe to the JSearch API
   - URL: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
   - Free tier available with limited requests

### Configuration

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Add your RapidAPI key to `.env`:
   ```bash
   RAPIDAPI_KEY=your_actual_rapidapi_key_here
   ```

3. Configure search parameters (optional):
   ```bash
   SEARCH_QUERIES=software engineer,data engineer,python developer
   SEARCH_LOCATION=United States
   NUM_PAGES=1
   RESULTS_PER_PAGE=10
   SCHEDULE_INTERVAL_MINUTES=60
   ```

### Running with Docker Compose

The service is already included in the main `docker compose.yml`:

```bash
# Start entire stack (includes LinkedIn ingestion)
docker compose up -d

# View ingestion logs
docker compose logs -f linkedin-ingestion

# Restart just the ingestion service
docker compose restart linkedin-ingestion
```

### Running Standalone

For development or testing:

```bash
# Install dependencies
cd api-ingestion
pip install -r requirements.txt

# Set environment variables
export RAPIDAPI_KEY=your_key_here
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=sourcedb
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres

# Run once
export RUN_MODE=once
python linkedin_ingestion.py

# Run with scheduler
export RUN_MODE=scheduler
python linkedin_ingestion.py
```

## Database Schema

The service creates a `linkedin_jobs` table with the following structure:

```sql
CREATE TABLE linkedin_jobs (
    job_id VARCHAR(255) PRIMARY KEY,
    job_title VARCHAR(500),
    company_name VARCHAR(500),
    location VARCHAR(500),
    job_description TEXT,
    employment_type VARCHAR(100),
    seniority_level VARCHAR(100),
    job_function VARCHAR(200),
    industries TEXT,
    posted_date TIMESTAMP,
    application_url TEXT,
    salary_min DECIMAL(10, 2),
    salary_max DECIMAL(10, 2),
    salary_currency VARCHAR(10),
    salary_period VARCHAR(50),
    remote_allowed BOOLEAN,
    company_logo_url TEXT,
    company_linkedin_url TEXT,
    required_skills TEXT,
    search_query VARCHAR(200),
    raw_data JSONB,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAPIDAPI_KEY` | (required) | Your RapidAPI key |
| `RAPIDAPI_HOST` | `jsearch.p.rapidapi.com` | RapidAPI host |
| `POSTGRES_HOST` | `postgres` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `sourcedb` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `SEARCH_QUERIES` | `software engineer,...` | Comma-separated search queries |
| `SEARCH_LOCATION` | `United States` | Job search location |
| `NUM_PAGES` | `1` | Number of pages to fetch per query |
| `RESULTS_PER_PAGE` | `10` | Results per page |
| `SCHEDULE_INTERVAL_MINUTES` | `60` | Minutes between ingestion runs |
| `RUN_MODE` | `scheduler` | `scheduler` or `once` |
| `LOG_LEVEL` | `INFO` | Logging level |

### Search Queries

Customize the job searches by editing `SEARCH_QUERIES`:

```bash
# Multiple roles
SEARCH_QUERIES=software engineer,data scientist,devops engineer,ml engineer

# Specific technologies
SEARCH_QUERIES=python developer,react developer,kubernetes engineer

# Locations (combined with SEARCH_LOCATION)
SEARCH_LOCATION=San Francisco,New York,Remote
```

### Schedule Configuration

Control how often the service fetches new data:

```bash
# Every 30 minutes
SCHEDULE_INTERVAL_MINUTES=30

# Every 2 hours
SCHEDULE_INTERVAL_MINUTES=120

# Every 6 hours
SCHEDULE_INTERVAL_MINUTES=360
```

## How It Works

### 1. Initialization
- Creates database tables if they don't exist
- Sets up PostgreSQL connection pool
- Configures replica identity for CDC

### 2. Data Fetching
- Calls RapidAPI JSearch LinkedIn API
- Paginates through results based on `NUM_PAGES`
- Respects rate limits with delays

### 3. Data Parsing
- Extracts relevant job information
- Normalizes data format
- Stores raw JSON for reference

### 4. Database Storage
- Uses UPSERT (INSERT ... ON CONFLICT UPDATE)
- Updates existing jobs if they already exist
- Triggers database update timestamp

### 5. CDC Event Generation
- PostgreSQL changes trigger Debezium
- Debezium publishes to Kafka topic `cdc.linkedin_jobs`
- CDC consumer loads data to Snowflake

## API Response Structure

The JSearch API returns job data in this format:

```json
{
  "data": [
    {
      "job_id": "abc123",
      "job_title": "Software Engineer",
      "employer_name": "Tech Company",
      "job_city": "San Francisco",
      "job_country": "US",
      "job_description": "...",
      "job_employment_type": "FULLTIME",
      "job_posted_at_datetime_utc": "2024-01-15T10:00:00Z",
      "job_apply_link": "https://...",
      "job_salary_min": 120000,
      "job_salary_max": 180000,
      "job_salary_currency": "USD",
      "job_is_remote": true,
      "employer_logo": "https://...",
      "job_required_skills": ["Python", "SQL", "AWS"]
    }
  ]
}
```

## Monitoring

### Check Ingestion Status

```bash
# View service logs
docker compose logs -f linkedin-ingestion

# Check last ingestion time
docker exec postgres psql -U postgres -d sourcedb \
  -c "SELECT MAX(last_updated_at) FROM linkedin_jobs;"

# Count jobs by search query
docker exec postgres psql -U postgres -d sourcedb \
  -c "SELECT search_query, COUNT(*) FROM linkedin_jobs GROUP BY search_query;"
```

### View Recent Jobs

```bash
# Most recent jobs
docker exec postgres psql -U postgres -d sourcedb \
  -c "SELECT job_id, job_title, company_name, posted_date
      FROM linkedin_jobs
      ORDER BY first_seen_at DESC
      LIMIT 10;"
```

### Check CDC Events

```bash
# View CDC events in Kafka
docker exec kafka kafka-console-consumer \
  --bootstrap-server localhost:29092 \
  --topic cdc.linkedin_jobs \
  --from-beginning \
  --max-messages 5
```

## Troubleshooting

### API Key Issues

**Error**: "Missing required environment variables: RAPIDAPI_KEY"

**Solution**:
1. Ensure `.env` file exists with `RAPIDAPI_KEY`
2. Verify API key is valid on RapidAPI dashboard
3. Check subscription is active

### No Jobs Fetched

**Issue**: Service runs but no jobs are stored

**Check**:
1. API response:
   ```bash
   docker compose logs linkedin-ingestion | grep "Fetched"
   ```

2. Database connection:
   ```bash
   docker exec postgres psql -U postgres -d sourcedb -c "\dt"
   ```

3. API quota:
   - Check RapidAPI dashboard for quota limits
   - Verify requests aren't being rate-limited

### Database Connection Errors

**Error**: "Failed to create database pool"

**Solution**:
1. Ensure PostgreSQL is running:
   ```bash
   docker compose ps postgres
   ```

2. Check credentials in `.env`

3. Verify network connectivity:
   ```bash
   docker exec linkedin-ingestion ping postgres
   ```

### CDC Events Not Appearing

**Issue**: Jobs stored in PostgreSQL but no Kafka events

**Check**:
1. Debezium connector status:
   ```bash
   curl http://localhost:8083/connectors/postgres-cdc-connector/status
   ```

2. Table included in connector config:
   ```bash
   grep linkedin_jobs connectors/postgres-connector.json
   ```

3. Redeploy connector:
   ```bash
   cd connectors && ./deploy-connector.sh
   ```

## Performance Tuning

### High Volume Ingestion

For fetching large numbers of jobs:

```bash
# Increase pages per query
NUM_PAGES=5

# More results per page (check API limits)
RESULTS_PER_PAGE=20

# Reduce frequency to avoid rate limits
SCHEDULE_INTERVAL_MINUTES=120
```

### Low Latency

For near-real-time updates:

```bash
# Frequent updates
SCHEDULE_INTERVAL_MINUTES=15

# Single page for speed
NUM_PAGES=1
RESULTS_PER_PAGE=10
```

## Development

### Running Tests

```bash
# Unit tests
pytest tests/

# Integration test (requires running PostgreSQL)
RUN_MODE=once python linkedin_ingestion.py
```

### Adding Custom Fields

To extract additional fields from the API:

1. Update `parse_job_data()` in `linkedin_ingestion.py`
2. Add new column to `ensure_tables_exist()`
3. Restart service to apply schema changes

### Custom Transformations

Add data transformations before storage:

```python
def parse_job_data(self, job: Dict, search_query: str) -> Dict:
    parsed = {
        # ... existing parsing
    }

    # Custom transformation
    if parsed['job_title']:
        parsed['job_title'] = parsed['job_title'].title()

    return parsed
```

## RapidAPI JSearch Pricing

| Plan | Price | Requests/Month |
|------|-------|----------------|
| Free | $0 | 250 |
| Basic | $9.99 | 5,000 |
| Pro | $39.99 | 25,000 |
| Ultra | $99.99 | 100,000 |

Check current pricing at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch/pricing

## Security Best Practices

1. **Never commit API keys**: Always use `.env` file
2. **Rotate keys regularly**: Change RapidAPI key periodically
3. **Limit permissions**: Use read-only database user where possible
4. **Monitor usage**: Track API quota to avoid overages
5. **Secure logs**: Ensure logs don't contain sensitive data

## Future Enhancements

Potential improvements:

- [ ] Support for multiple job boards (Indeed, Glassdoor, etc.)
- [ ] Deduplication across different sources
- [ ] Job change detection and alerting
- [ ] Skills extraction and categorization
- [ ] Salary trend analysis
- [ ] Company information enrichment
- [ ] Webhook support for real-time updates

## Resources

- [RapidAPI JSearch Documentation](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Debezium PostgreSQL Connector](https://debezium.io/documentation/reference/stable/connectors/postgresql.html)

## Support

For issues:
1. Check logs: `docker compose logs linkedin-ingestion`
2. Review troubleshooting section above
3. Open GitHub issue with logs and configuration (redact sensitive data)
