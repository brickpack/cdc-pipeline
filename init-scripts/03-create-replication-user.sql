-- Create replication user for Debezium connector
-- This user needs specific permissions for CDC functionality
-- Note: This script is templated and replaced by 03-create-replication-user.sh at runtime

-- Create replication user
-- Password is set via DEBEZIUM_PASSWORD environment variable
DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'debezium') THEN
        EXECUTE format('CREATE USER debezium WITH PASSWORD %L REPLICATION', current_setting('debezium.password'));
    END IF;
END
$$;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO debezium;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO debezium;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO debezium;

-- Grant replication-specific permissions
ALTER USER debezium WITH REPLICATION;

-- Create publication for logical replication
-- This publication includes all tables in the public schema
CREATE PUBLICATION dbz_publication FOR ALL TABLES;

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
