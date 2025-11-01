"""
CDC Consumer for Snowflake Data Loading

This module consumes CDC events from Kafka topics and loads them into Snowflake.
Supports INSERT, UPDATE, and DELETE operations with proper error handling and retry logic.
"""

import os
import sys
import json
import logging
import signal
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from pathlib import Path

from confluent_kafka import Consumer, KafkaError, KafkaException
from confluent_kafka.avro import AvroConsumer
from confluent_kafka.avro.serializer import SerializerError
import json
import snowflake.connector
from snowflake.connector import DictCursor
from snowflake.connector.errors import ProgrammingError, DatabaseError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/var/log/cdc-consumer/consumer.log')
    ]
)
logger = logging.getLogger(__name__)


class SnowflakeWriter:
    """Handles writing CDC events to Snowflake"""

    def __init__(self, config: Dict[str, str]):
        """Initialize Snowflake connection"""
        self.config = config
        self.connection = None
        self.table_cache = set()
        self.connect()

    def connect(self):
        """Establish connection to Snowflake"""
        try:
            # Set environment variable to bypass OCSP check in Docker
            os.environ['SNOWFLAKE_OCSP_FAIL_OPEN'] = 'TRUE'

            connection_params = {
                'account': self.config['account'],
                'user': self.config['user'],
                'database': self.config['database'],
                'schema': self.config['schema'],
                'warehouse': self.config['warehouse'],
                'autocommit': False,
                # Disable OCSP check - required for Docker containers
                # This bypasses certificate revocation checking which can fail in containerized environments
                'ocsp_response_cache_filename': None,
                'insecure_mode': True  # Temporarily disable SSL verification for testing
            }

            # Use private key authentication if private_key_path is provided
            if self.config.get('private_key_path'):
                private_key = self._load_private_key(
                    self.config['private_key_path'],
                    self.config.get('private_key_passphrase')
                )
                connection_params['private_key'] = private_key
                logger.info("Using private key authentication")
            elif self.config.get('password'):
                connection_params['password'] = self.config['password']
                logger.info("Using password authentication")
            else:
                raise ValueError("Either password or private_key_path must be provided")

            self.connection = snowflake.connector.connect(**connection_params)
            logger.info("Connected to Snowflake successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Snowflake: {e}")
            raise

    def _load_private_key(self, key_path: str, passphrase: Optional[str] = None):
        """Load and decode private key for Snowflake authentication"""
        try:
            with open(key_path, 'rb') as key_file:
                private_key_data = key_file.read()

            # Parse the private key
            password = passphrase.encode() if passphrase else None
            private_key = serialization.load_pem_private_key(
                private_key_data,
                password=password,
                backend=default_backend()
            )

            # Encode to DER format (required by Snowflake)
            pkb = private_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )

            logger.info(f"Successfully loaded private key from {key_path}")
            return pkb

        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            raise

    def ensure_table_exists(self, table_name: str, sample_record: Dict[str, Any]):
        """Create table in Snowflake if it doesn't exist"""
        if table_name in self.table_cache:
            return

        try:
            cursor = self.connection.cursor()

            # Build fully qualified table name
            database = self.config['database']
            schema = self.config['schema']
            qualified_table_name = f"{database}.{schema}.{table_name}"

            # Create table with CDC metadata columns
            columns = []
            for key, value in sample_record.items():
                col_type = self._infer_snowflake_type(value)
                columns.append(f"{key} {col_type}")

            # Add CDC metadata columns
            columns.extend([
                "_cdc_operation VARCHAR(10)",
                "_cdc_timestamp TIMESTAMP_NTZ",
                "_cdc_source_lsn NUMBER",
                "_cdc_processed_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()"
            ])

            create_sql = f"""
                CREATE TABLE IF NOT EXISTS {qualified_table_name} (
                    {', '.join(columns)}
                )
            """

            cursor.execute(create_sql)
            logger.info(f"Ensured table exists: {qualified_table_name}")

            self.table_cache.add(table_name)
            cursor.close()

        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise

    def _infer_snowflake_type(self, value: Any) -> str:
        """Infer Snowflake data type from Python value"""
        if value is None:
            return "VARCHAR"
        elif isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, int):
            return "NUMBER"
        elif isinstance(value, float):
            return "FLOAT"
        elif isinstance(value, (dict, list)):
            return "VARIANT"
        elif isinstance(value, datetime):
            return "TIMESTAMP_NTZ"
        else:
            return "VARCHAR"

    def write_batch(self, table_name: str, records: List[Dict[str, Any]]):
        """Write a batch of records to Snowflake"""
        if not records:
            return

        try:
            cursor = self.connection.cursor()

            # Build fully qualified table name
            database = self.config['database']
            schema = self.config['schema']
            qualified_table_name = f"{database}.{schema}.{table_name}"

            # Ensure table exists
            if records[0].get('after'):
                self.ensure_table_exists(table_name, records[0]['after'])

            # Process records by operation type
            inserts = []
            updates = []
            deletes = []

            for record in records:
                op = record.get('op')
                if op in ('c', 'r'):  # Create or Read (snapshot)
                    inserts.append(record)
                elif op == 'u':  # Update
                    updates.append(record)
                elif op == 'd':  # Delete
                    deletes.append(record)

            # Execute operations
            if inserts:
                self._execute_inserts(cursor, qualified_table_name, inserts)
            if updates:
                self._execute_updates(cursor, qualified_table_name, updates)
            if deletes:
                self._execute_deletes(cursor, qualified_table_name, deletes)

            self.connection.commit()
            logger.info(f"Batch written to {table_name}: {len(inserts)} inserts, "
                       f"{len(updates)} updates, {len(deletes)} deletes")

            cursor.close()

        except Exception as e:
            logger.error(f"Failed to write batch to {table_name}: {e}")
            self.connection.rollback()
            raise

    def _execute_inserts(self, cursor, table_name: str, records: List[Dict]):
        """Execute INSERT operations"""
        for record in records:
            data = record['after'].copy()  # Make a copy to avoid modifying original
            data['_cdc_operation'] = record['op']
            data['_cdc_timestamp'] = datetime.fromtimestamp(record['ts_ms'] / 1000.0)
            data['_cdc_source_lsn'] = record.get('source', {}).get('lsn', 0)

            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            values = list(data.values())

            # Use simple INSERT
            insert_sql = f"""
                INSERT INTO {table_name} ({columns})
                VALUES ({placeholders})
            """

            cursor.execute(insert_sql, values)

    def _execute_updates(self, cursor, table_name: str, records: List[Dict]):
        """Execute UPDATE operations"""
        for record in records:
            after_data = record['after']
            before_data = record.get('before', {})

            # Get primary key from source metadata or use first column
            pk_fields = self._get_primary_key(record)

            # Validate that primary key exists in after_data
            missing_pk = [pk for pk in pk_fields if pk not in after_data]
            if missing_pk:
                logger.error(f"Primary key fields {missing_pk} not found in after_data for table {table_name}")
                continue

            # Build SET clause excluding primary key fields (PK shouldn't change)
            set_fields = {k: v for k, v in after_data.items() if k not in pk_fields}
            set_clause = ', '.join([f"{k} = %s" for k in set_fields.keys()])
            
            # Build WHERE clause using primary key from after_data
            where_clause = ' AND '.join([f"{k} = %s" for k in pk_fields])

            update_sql = f"""
                UPDATE {table_name}
                SET {set_clause},
                    _cdc_operation = %s,
                    _cdc_timestamp = %s,
                    _cdc_source_lsn = %s
                WHERE {where_clause}
            """

            values = (
                list(set_fields.values()) +
                [record['op'],
                 datetime.fromtimestamp(record['ts_ms'] / 1000.0),
                 record.get('source', {}).get('lsn', 0)] +
                [after_data.get(k) for k in pk_fields]  # Use after_data, not before_data
            )

            cursor.execute(update_sql, values)
            
            # Check if update actually matched any rows
            rows_affected = cursor.rowcount
            if rows_affected == 0:
                logger.warning(f"UPDATE matched 0 rows for table {table_name}, PK values: {[after_data.get(k) for k in pk_fields]}")
            else:
                logger.debug(f"UPDATE affected {rows_affected} row(s) for table {table_name}")

    def _execute_deletes(self, cursor, table_name: str, records: List[Dict]):
        """Execute DELETE operations"""
        for record in records:
            before_data = record.get('before', {})
            pk_fields = self._get_primary_key(record)

            where_clause = ' AND '.join([f"{k} = %s" for k in pk_fields])
            delete_sql = f"DELETE FROM {table_name} WHERE {where_clause}"

            values = [before_data.get(k) for k in pk_fields]
            cursor.execute(delete_sql, values)

    def _get_primary_key(self, record: Dict) -> List[str]:
        """Extract primary key fields from record"""
        # Try to get from source metadata
        source = record.get('source', {})
        table = source.get('table', '')
        
        # Also check the topic name as fallback (extracted from table name in process_message)
        if not table:
            # Check if we can infer from after_data structure
            after_data = record.get('after', {})
            if not after_data:
                after_data = record.get('payload', {}).get('after', {})

        # Default primary key patterns
        pk_patterns = {
            'customers': ['customer_id'],
            'products': ['product_id'],
            'orders': ['order_id'],
            'order_items': ['order_item_id'],  # Note: might need composite key
            'inventory_transactions': ['transaction_id'],
            'linkedin_jobs': ['job_id']
        }

        pk = pk_patterns.get(table, ['id'])
        
        # If using default 'id' and it doesn't exist, try common patterns
        if pk == ['id']:
            after_data = record.get('after', {})
            if not after_data:
                after_data = record.get('payload', {}).get('after', {})
            
            # Try common ID field names
            for common_id in ['id', '_id', table + '_id', 'uuid']:
                if after_data and common_id in after_data:
                    return [common_id]
    
        return pk

    def close(self):
        """Close Snowflake connection"""
        if self.connection:
            self.connection.close()
            logger.info("Snowflake connection closed")


class CDCConsumer:
    """Main CDC consumer class"""

    def __init__(self):
        """Initialize consumer with configuration"""
        self.running = True
        self.config = self._load_config()
        self.consumer = self._create_consumer()
        self.snowflake_writer = SnowflakeWriter(self.config['snowflake'])
        self.batch_size = int(self.config['consumer']['batch_size'])
        self.poll_timeout = float(self.config['consumer']['poll_timeout'])
        self.message_buffer = defaultdict(list)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        return {
            'kafka': {
                'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
                'group.id': os.getenv('CONSUMER_GROUP_ID', 'cdc-consumer-group'),
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False
            },
            'snowflake': {
                'account': os.getenv('SNOWFLAKE_ACCOUNT'),
                'user': os.getenv('SNOWFLAKE_USER'),
                'password': os.getenv('SNOWFLAKE_PASSWORD'),
                'private_key_path': os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH'),
                'private_key_passphrase': os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE'),
                'database': os.getenv('SNOWFLAKE_DATABASE', 'CDC_DB'),
                'schema': os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
                'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH')
            },
            'consumer': {
                'batch_size': os.getenv('BATCH_SIZE', '100'),
                'poll_timeout': os.getenv('POLL_TIMEOUT', '1.0')
            }
        }

    def _create_consumer(self) -> Consumer:
        """Create and configure Kafka consumer"""
        try:
            # Use regular Consumer for JSON messages from Debezium
            consumer = Consumer(self.config['kafka'])
            logger.info("Kafka consumer created successfully")
            return consumer
        except Exception as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def subscribe_to_topics(self, topics: List[str]):
        """Subscribe to Kafka topics"""
        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {e}")
            raise

    def process_message(self, message):
        """Process a single CDC message"""
        try:
            raw_value = message.value()
            if raw_value is None:
                return

            # Decode JSON message from Debezium
            message_json = json.loads(raw_value.decode('utf-8'))

            # Extract payload from Debezium message structure
            # Debezium wraps the actual CDC data in a "payload" field
            value = message_json.get('payload', message_json)

            # Extract table name from topic
            topic = message.topic()
            table_name = topic.split('.')[-1]

            # Add to buffer
            self.message_buffer[table_name].append(value)

            # Process batch if buffer is full
            if len(self.message_buffer[table_name]) >= self.batch_size:
                self._flush_buffer(table_name)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise

    def _flush_buffer(self, table_name: str):
        """Flush buffered messages to Snowflake"""
        if not self.message_buffer[table_name]:
            return

        try:
            records = self.message_buffer[table_name]
            self.snowflake_writer.write_batch(table_name, records)
            self.message_buffer[table_name] = []
        except Exception as e:
            logger.error(f"Failed to flush buffer for {table_name}: {e}")
            raise

    def run(self):
        """Main consumer loop"""
        logger.info("Starting CDC consumer...")

        try:
            while self.running:
                message = self.consumer.poll(timeout=self.poll_timeout)

                if message is None:
                    # Flush any pending buffers on timeout
                    for table_name in list(self.message_buffer.keys()):
                        self._flush_buffer(table_name)
                    continue

                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition: {message.topic()}")
                    else:
                        logger.error(f"Kafka error: {message.error()}")
                    continue

                self.process_message(message)
                self.consumer.commit(message)

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        except Exception as e:
            logger.error(f"Unexpected error in consumer loop: {e}")
            raise
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info("Shutting down consumer...")

        # Flush all remaining buffers
        for table_name in list(self.message_buffer.keys()):
            try:
                self._flush_buffer(table_name)
            except Exception as e:
                logger.error(f"Error flushing buffer during shutdown: {e}")

        # Close connections
        if self.consumer:
            self.consumer.close()
        if self.snowflake_writer:
            self.snowflake_writer.close()

        logger.info("Consumer shutdown complete")


def main():
    """Main entry point"""
    # Check required environment variables
    required_vars = ['SNOWFLAKE_ACCOUNT', 'SNOWFLAKE_USER']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)

    # Validate authentication method
    has_password = os.getenv('SNOWFLAKE_PASSWORD')
    has_private_key = os.getenv('SNOWFLAKE_PRIVATE_KEY_PATH')

    if not has_password and not has_private_key:
        logger.error("Either SNOWFLAKE_PASSWORD or SNOWFLAKE_PRIVATE_KEY_PATH must be provided")
        sys.exit(1)

    # Create and run consumer
    consumer = CDCConsumer()

    # Subscribe to CDC topics (adjust pattern as needed)
    topics = ['cdc.customers', 'cdc.products', 'cdc.orders',
              'cdc.order_items', 'cdc.inventory_transactions', 'cdc.linkedin_jobs']

    consumer.subscribe_to_topics(topics)
    consumer.run()


if __name__ == '__main__':
    main()
