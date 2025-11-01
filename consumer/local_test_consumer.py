"""
Local Test Consumer for CDC Pipeline

This consumer prints CDC events to console instead of writing to Snowflake.
Useful for testing the pipeline locally without Snowflake credentials.

Note: This consumer expects JSON-serialized messages from Debezium.
"""

import os
import sys
import logging
import signal
import json
from typing import List
from confluent_kafka import Consumer, KafkaError


# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LocalTestConsumer:
    """Test consumer that logs messages instead of writing to database"""

    def __init__(self):
        self.running = True
        self.message_count = 0
        self.config = {
            'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
            'group.id': os.getenv('CONSUMER_GROUP_ID', 'local-test-consumer'),
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
        }

        # Use regular Consumer for JSON messages (not AvroConsumer)
        self.consumer = Consumer(self.config)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def subscribe_to_topics(self, topics: List[str]):
        """Subscribe to Kafka topics"""
        try:
            self.consumer.subscribe(topics)
            logger.info(f"Subscribed to topics: {topics}")
        except Exception as e:
            logger.error(f"Failed to subscribe to topics: {e}")
            raise

    def format_message(self, value: dict) -> str:
        """Format CDC message for display"""
        operation_names = {
            'c': 'CREATE',
            'u': 'UPDATE',
            'd': 'DELETE',
            'r': 'READ (snapshot)'
        }

        op = value.get('op', 'unknown')
        op_name = operation_names.get(op, op)

        before = value.get('before')
        after = value.get('after')
        source = value.get('source', {})
        ts_ms = value.get('ts_ms', 0)

        output = [
            f"\n{'='*80}",
            f"Operation: {op_name}",
            f"Table: {source.get('table', 'unknown')}",
            f"Timestamp: {ts_ms}",
            f"LSN: {source.get('lsn', 'N/A')}",
        ]

        if before:
            output.append(f"\nBefore: {json.dumps(before, indent=2)}")

        if after:
            output.append(f"\nAfter: {json.dumps(after, indent=2)}")

        output.append(f"{'='*80}")

        return '\n'.join(output)

    def process_message(self, message):
        """Process and display CDC message"""
        try:
            raw_value = message.value()
            if raw_value is None:
                logger.info("Received tombstone message (delete marker)")
                return

            # Decode JSON message from Debezium
            message_json = json.loads(raw_value.decode('utf-8'))

            # Extract payload from Debezium message structure
            # Debezium wraps the actual CDC data in a "payload" field
            value = message_json.get('payload', message_json)

            self.message_count += 1
            topic = message.topic()
            partition = message.partition()
            offset = message.offset()

            logger.info(f"\n[Message #{self.message_count}] Topic: {topic}, "
                       f"Partition: {partition}, Offset: {offset}")

            print(self.format_message(value))

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

    def run(self):
        """Main consumer loop"""
        logger.info("Starting local test consumer...")
        logger.info("Press Ctrl+C to stop")

        try:
            while self.running:
                message = self.consumer.poll(timeout=1.0)

                if message is None:
                    continue

                if message.error():
                    if message.error().code() == KafkaError._PARTITION_EOF:
                        logger.debug(f"Reached end of partition: {message.topic()}")
                    else:
                        logger.error(f"Kafka error: {message.error()}")
                    continue

                self.process_message(message)

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
        finally:
            self.shutdown()

    def shutdown(self):
        """Cleanup and shutdown"""
        logger.info(f"\nShutting down... Processed {self.message_count} messages")
        if self.consumer:
            self.consumer.close()
        logger.info("Consumer shutdown complete")


def main():
    """Main entry point"""
    consumer = LocalTestConsumer()

    # Subscribe to all CDC topics
    topics = ['cdc.customers', 'cdc.products', 'cdc.orders',
              'cdc.order_items', 'cdc.inventory_transactions', 'cdc.linkedin_jobs']

    print("\n" + "="*80)
    print("LOCAL TEST CONSUMER")
    print("="*80)
    print(f"Kafka: {os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')}")
    print(f"Consumer Group: {os.getenv('CONSUMER_GROUP_ID', 'local-test-consumer')}")
    print(f"Topics: {', '.join(topics)}")
    print(f"Format: JSON (Debezium)")
    print("="*80 + "\n")

    consumer.subscribe_to_topics(topics)
    consumer.run()


if __name__ == '__main__':
    main()
