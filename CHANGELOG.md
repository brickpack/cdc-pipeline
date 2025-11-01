# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Fixed
- **PostgreSQL initialization**: Removed invalid `POSTGRES_INITDB_ARGS` that was causing container startup failures
- **Debezium connector**: Fixed Avro converter error by switching to JSON converters (Debezium image doesn't include Confluent Avro converter)
- **Publication mode**: Changed connector publication mode from `filtered` to `all_tables` to work with existing PostgreSQL publication
- **UPDATE operations**: Fixed critical bug where UPDATE statements weren't working - now correctly uses primary key from `after` data instead of `before` data
- **Monitoring stack**: Fixed network declaration in monitoring compose file - removed external network dependency
- **Docker Compose**: Removed obsolete `version` attribute from compose files (not required in Compose v2)

### Improved
- **Primary key detection**: Enhanced `_get_primary_key()` method with better fallback logic and support for `linkedin_jobs` table
- **UPDATE validation**: Added validation to ensure primary key fields exist before executing UPDATE statements
- **Error logging**: Added warning logs when UPDATE operations match zero rows (helps debug data sync issues)
- **JMX exporter**: Temporarily disabled Kafka JMX exporter due to platform compatibility and configuration complexity (Kafka UI provides basic metrics)

### Changed
- **Message format**: Switched from Avro to JSON for Kafka messages (simpler, no Schema Registry dependency)
- **Publication handling**: Connector now uses `all_tables` mode to work with pre-existing PostgreSQL publication

## [1.0.0] - Initial Release

### Added
- Real-time CDC pipeline with Debezium, Kafka, and Snowflake
- LinkedIn job ingestion from RapidAPI
- Comprehensive monitoring stack (Prometheus, Grafana, Loki)
- Docker-based local development environment
- Automated setup scripts
- Complete documentation

