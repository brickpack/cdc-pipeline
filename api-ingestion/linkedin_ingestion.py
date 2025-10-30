"""
LinkedIn Job Data Ingestion Service

Fetches job data from RapidAPI JSearch LinkedIn API and stores it in PostgreSQL.
Changes in PostgreSQL trigger CDC events through Debezium.
"""

import os
import sys
import time
import logging
import signal
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

import requests
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2 import pool
import schedule


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/api-ingestion/ingestion.log')
    ]
)
logger = logging.getLogger(__name__)


class LinkedInJobIngestion:
    """Ingests LinkedIn job data from RapidAPI JSearch"""

    def __init__(self):
        """Initialize the ingestion service"""
        self.running = True
        self.config = self._load_config()
        self.db_pool = self._create_db_pool()
        self.session = requests.Session()
        self.stats = defaultdict(int)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        rapidapi_key = os.getenv('RAPIDAPI_KEY')
        if not rapidapi_key:
            logger.error("RAPIDAPI_KEY environment variable not set")
            raise ValueError("RAPIDAPI_KEY is required")

        return {
            'rapidapi': {
                'key': rapidapi_key,
                'host': os.getenv('RAPIDAPI_HOST', 'jsearch.p.rapidapi.com'),
                'endpoint': 'https://jsearch.p.rapidapi.com/search'
            },
            'database': {
                'host': os.getenv('POSTGRES_HOST', 'postgres'),
                'port': int(os.getenv('POSTGRES_PORT', '5432')),
                'database': os.getenv('POSTGRES_DB', 'sourcedb'),
                'user': os.getenv('POSTGRES_USER', 'postgres'),
                'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
            },
            'ingestion': {
                'search_queries': os.getenv('SEARCH_QUERIES', 'software engineer,data engineer,python developer').split(','),
                'location': os.getenv('SEARCH_LOCATION', 'United States'),
                'num_pages': int(os.getenv('NUM_PAGES', '1')),
                'results_per_page': int(os.getenv('RESULTS_PER_PAGE', '10')),
                'schedule_interval': int(os.getenv('SCHEDULE_INTERVAL_MINUTES', '60'))
            }
        }

    def _create_db_pool(self) -> pool.SimpleConnectionPool:
        """Create PostgreSQL connection pool"""
        try:
            db_pool = pool.SimpleConnectionPool(
                1, 10,
                host=self.config['database']['host'],
                port=self.config['database']['port'],
                database=self.config['database']['database'],
                user=self.config['database']['user'],
                password=self.config['database']['password']
            )
            logger.info("Database connection pool created")
            return db_pool
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def _get_db_connection(self):
        """Get connection from pool"""
        return self.db_pool.getconn()

    def _return_db_connection(self, conn):
        """Return connection to pool"""
        self.db_pool.putconn(conn)

    def ensure_tables_exist(self):
        """Create tables if they don't exist"""
        conn = self._get_db_connection()
        try:
            cursor = conn.cursor()

            # Create linkedin_jobs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS linkedin_jobs (
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
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_linkedin_jobs_company
                ON linkedin_jobs(company_name)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_linkedin_jobs_location
                ON linkedin_jobs(location)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_linkedin_jobs_posted_date
                ON linkedin_jobs(posted_date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_linkedin_jobs_search_query
                ON linkedin_jobs(search_query)
            """)

            # Create trigger for updated_at
            cursor.execute("""
                CREATE OR REPLACE FUNCTION update_linkedin_jobs_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.last_updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """)

            cursor.execute("""
                DROP TRIGGER IF EXISTS update_linkedin_jobs_updated_at ON linkedin_jobs
            """)

            cursor.execute("""
                CREATE TRIGGER update_linkedin_jobs_updated_at
                BEFORE UPDATE ON linkedin_jobs
                FOR EACH ROW
                EXECUTE FUNCTION update_linkedin_jobs_timestamp()
            """)

            # Set replica identity for CDC
            cursor.execute("""
                ALTER TABLE linkedin_jobs REPLICA IDENTITY FULL
            """)

            conn.commit()
            logger.info("LinkedIn jobs table ensured")
            cursor.close()

        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            conn.rollback()
            raise
        finally:
            self._return_db_connection(conn)

    def fetch_jobs(self, query: str, page: int = 1) -> Optional[Dict]:
        """Fetch jobs from RapidAPI JSearch LinkedIn API"""
        try:
            headers = {
                'X-RapidAPI-Key': self.config['rapidapi']['key'],
                'X-RapidAPI-Host': self.config['rapidapi']['host']
            }

            params = {
                'query': f"{query} in {self.config['ingestion']['location']}",
                'page': str(page),
                'num_pages': '1',
                'date_posted': 'all'
            }

            logger.info(f"Fetching jobs for query: '{query}', page: {page}")

            response = self.session.get(
                self.config['rapidapi']['endpoint'],
                headers=headers,
                params=params,
                timeout=30
            )

            response.raise_for_status()
            data = response.json()

            logger.info(f"Fetched {len(data.get('data', []))} jobs for query: '{query}'")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching jobs: {e}")
            return None

    def parse_job_data(self, job: Dict, search_query: str) -> Dict:
        """Parse job data from API response"""
        try:
            # Extract salary information
            salary_min = None
            salary_max = None
            salary_currency = None
            salary_period = None

            if 'job_salary_min' in job:
                salary_min = job.get('job_salary_min')
            if 'job_salary_max' in job:
                salary_max = job.get('job_salary_max')
            if 'job_salary_currency' in job:
                salary_currency = job.get('job_salary_currency')
            if 'job_salary_period' in job:
                salary_period = job.get('job_salary_period')

            # Parse posted date
            posted_date = None
            if 'job_posted_at_datetime_utc' in job:
                try:
                    posted_date = datetime.fromisoformat(
                        job['job_posted_at_datetime_utc'].replace('Z', '+00:00')
                    )
                except Exception:
                    posted_date = datetime.utcnow()

            # Extract skills
            required_skills = None
            if 'job_required_skills' in job and job['job_required_skills']:
                required_skills = ','.join(job['job_required_skills'])

            return {
                'job_id': job.get('job_id', ''),
                'job_title': job.get('job_title', '')[:500],
                'company_name': job.get('employer_name', '')[:500],
                'location': job.get('job_city', '') or job.get('job_country', ''),
                'job_description': job.get('job_description', ''),
                'employment_type': job.get('job_employment_type', '')[:100],
                'seniority_level': job.get('job_seniority_level', '')[:100],
                'job_function': job.get('job_function', '')[:200],
                'industries': job.get('job_industry', ''),
                'posted_date': posted_date,
                'application_url': job.get('job_apply_link', ''),
                'salary_min': salary_min,
                'salary_max': salary_max,
                'salary_currency': salary_currency,
                'salary_period': salary_period,
                'remote_allowed': job.get('job_is_remote', False),
                'company_logo_url': job.get('employer_logo', ''),
                'company_linkedin_url': job.get('employer_company_type', ''),
                'required_skills': required_skills,
                'search_query': search_query,
                'raw_data': json.dumps(job)
            }

        except Exception as e:
            logger.error(f"Error parsing job data: {e}")
            return None

    def store_jobs(self, jobs: List[Dict]):
        """Store jobs in PostgreSQL using UPSERT"""
        if not jobs:
            return

        conn = self._get_db_connection()
        try:
            cursor = conn.cursor()

            # Prepare data for bulk insert/update
            values = [
                (
                    job['job_id'],
                    job['job_title'],
                    job['company_name'],
                    job['location'],
                    job['job_description'],
                    job['employment_type'],
                    job['seniority_level'],
                    job['job_function'],
                    job['industries'],
                    job['posted_date'],
                    job['application_url'],
                    job['salary_min'],
                    job['salary_max'],
                    job['salary_currency'],
                    job['salary_period'],
                    job['remote_allowed'],
                    job['company_logo_url'],
                    job['company_linkedin_url'],
                    job['required_skills'],
                    job['search_query'],
                    job['raw_data']
                )
                for job in jobs
            ]

            # UPSERT query
            insert_query = """
                INSERT INTO linkedin_jobs (
                    job_id, job_title, company_name, location, job_description,
                    employment_type, seniority_level, job_function, industries,
                    posted_date, application_url, salary_min, salary_max,
                    salary_currency, salary_period, remote_allowed, company_logo_url,
                    company_linkedin_url, required_skills, search_query, raw_data
                )
                VALUES %s
                ON CONFLICT (job_id) DO UPDATE SET
                    job_title = EXCLUDED.job_title,
                    company_name = EXCLUDED.company_name,
                    location = EXCLUDED.location,
                    job_description = EXCLUDED.job_description,
                    employment_type = EXCLUDED.employment_type,
                    seniority_level = EXCLUDED.seniority_level,
                    job_function = EXCLUDED.job_function,
                    industries = EXCLUDED.industries,
                    posted_date = EXCLUDED.posted_date,
                    application_url = EXCLUDED.application_url,
                    salary_min = EXCLUDED.salary_min,
                    salary_max = EXCLUDED.salary_max,
                    salary_currency = EXCLUDED.salary_currency,
                    salary_period = EXCLUDED.salary_period,
                    remote_allowed = EXCLUDED.remote_allowed,
                    company_logo_url = EXCLUDED.company_logo_url,
                    company_linkedin_url = EXCLUDED.company_linkedin_url,
                    required_skills = EXCLUDED.required_skills,
                    search_query = EXCLUDED.search_query,
                    raw_data = EXCLUDED.raw_data,
                    is_active = true
            """

            execute_values(cursor, insert_query, values)
            conn.commit()

            self.stats['jobs_stored'] += len(jobs)
            logger.info(f"Stored {len(jobs)} jobs in database")

            cursor.close()

        except Exception as e:
            logger.error(f"Failed to store jobs: {e}")
            conn.rollback()
            raise
        finally:
            self._return_db_connection(conn)

    def run_ingestion(self):
        """Run a single ingestion cycle"""
        logger.info("Starting ingestion cycle")
        cycle_start = datetime.now()

        try:
            # Ensure tables exist
            self.ensure_tables_exist()

            total_jobs = 0

            # Iterate through search queries
            for query in self.config['ingestion']['search_queries']:
                query = query.strip()
                if not query:
                    continue

                # Fetch multiple pages if configured
                for page in range(1, self.config['ingestion']['num_pages'] + 1):
                    # Fetch jobs from API
                    response = self.fetch_jobs(query, page)

                    if not response or 'data' not in response:
                        logger.warning(f"No data returned for query: '{query}', page: {page}")
                        continue

                    jobs_data = response['data']
                    if not jobs_data:
                        logger.info(f"No jobs found for query: '{query}', page: {page}")
                        break

                    # Parse job data
                    parsed_jobs = []
                    for job in jobs_data:
                        parsed_job = self.parse_job_data(job, query)
                        if parsed_job and parsed_job['job_id']:
                            parsed_jobs.append(parsed_job)

                    # Store jobs in database
                    if parsed_jobs:
                        self.store_jobs(parsed_jobs)
                        total_jobs += len(parsed_jobs)

                    # Rate limiting - wait between requests
                    time.sleep(1)

            cycle_duration = (datetime.now() - cycle_start).total_seconds()
            logger.info(f"Ingestion cycle complete. Jobs processed: {total_jobs}, Duration: {cycle_duration:.2f}s")

            self.stats['cycles_completed'] += 1
            self.stats['total_jobs'] += total_jobs

        except Exception as e:
            logger.error(f"Error during ingestion cycle: {e}", exc_info=True)
            self.stats['cycles_failed'] += 1

    def print_stats(self):
        """Print ingestion statistics"""
        logger.info("=== Ingestion Statistics ===")
        logger.info(f"Cycles completed: {self.stats['cycles_completed']}")
        logger.info(f"Cycles failed: {self.stats['cycles_failed']}")
        logger.info(f"Total jobs processed: {self.stats['total_jobs']}")
        logger.info(f"Jobs stored: {self.stats['jobs_stored']}")

    def run_scheduler(self):
        """Run the ingestion service with scheduler"""
        logger.info("LinkedIn Job Ingestion Service started")
        logger.info(f"Search queries: {self.config['ingestion']['search_queries']}")
        logger.info(f"Location: {self.config['ingestion']['location']}")
        logger.info(f"Schedule interval: {self.config['ingestion']['schedule_interval']} minutes")

        # Run immediately on start
        self.run_ingestion()

        # Schedule periodic runs
        schedule.every(self.config['ingestion']['schedule_interval']).minutes.do(self.run_ingestion)

        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)

        self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("Shutting down ingestion service...")
        self.print_stats()

        if self.db_pool:
            self.db_pool.closeall()

        logger.info("Shutdown complete")


def main():
    """Main entry point"""
    # Check required environment variables
    if not os.getenv('RAPIDAPI_KEY'):
        logger.error("RAPIDAPI_KEY environment variable is required")
        sys.exit(1)

    # Create and run ingestion service
    ingestion_service = LinkedInJobIngestion()

    # Choose run mode
    run_mode = os.getenv('RUN_MODE', 'scheduler')

    if run_mode == 'once':
        # Run once and exit
        logger.info("Running in 'once' mode")
        ingestion_service.ensure_tables_exist()
        ingestion_service.run_ingestion()
        ingestion_service.print_stats()
    else:
        # Run with scheduler
        logger.info("Running in 'scheduler' mode")
        ingestion_service.run_scheduler()


if __name__ == '__main__':
    main()
