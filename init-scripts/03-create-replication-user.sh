#!/bin/bash
# Create replication user for Debezium connector
# This script uses environment variables for password configuration

set -e

# Get password from environment or use default
DEBEZIUM_PASSWORD="${DEBEZIUM_PASSWORD:-debezium_password}"

# Execute SQL to create user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create replication user
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'debezium') THEN
            CREATE USER debezium WITH PASSWORD '$DEBEZIUM_PASSWORD' REPLICATION;
        END IF;
    END
    \$\$;

    -- Grant necessary permissions
    GRANT USAGE ON SCHEMA public TO debezium;
    GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

    -- Grant replication-specific permissions
    ALTER USER debezium WITH REPLICATION;

    -- Create publication for logical replication
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'dbz_publication') THEN
            CREATE PUBLICATION dbz_publication FOR ALL TABLES;
        END IF;
    END
    \$\$;

    -- Grant permission on publication
    ALTER PUBLICATION dbz_publication OWNER TO debezium;

    -- Display confirmation
    SELECT 'Replication user created successfully!' AS status;
    SELECT
        usename AS username,
        userepl AS replication_enabled,
        usesuper AS is_superuser
    FROM pg_user
    WHERE usename = 'debezium';
EOSQL
