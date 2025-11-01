#!/usr/bin/env python3
"""
Quick script to verify data in Snowflake
"""
import os
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

# Load private key
def load_private_key(key_path):
    with open(key_path, 'rb') as key_file:
        private_key_data = key_file.read()

    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None,
        backend=default_backend()
    )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

# Connect to Snowflake
os.environ['SNOWFLAKE_OCSP_FAIL_OPEN'] = 'TRUE'

private_key = load_private_key('/Users/dave/.ssh/snowflake_key.p8')

conn = snowflake.connector.connect(
    account='BIB26482.us-west-2',
    user='BIRKBECK',
    warehouse='COMPUTE_WH',
    private_key=private_key,
    insecure_mode=True
)

cursor = conn.cursor()

# Create database if it doesn't exist
print("Creating CDC_DB database...")
cursor.execute("CREATE DATABASE IF NOT EXISTS CDC_DB")
print("✓ Database CDC_DB created/verified")

# Create schema
cursor.execute("CREATE SCHEMA IF NOT EXISTS CDC_DB.PUBLIC")
print("✓ Schema PUBLIC created/verified")

# Use the database
cursor.execute("USE DATABASE CDC_DB")
cursor.execute("USE SCHEMA PUBLIC")

# Check if table exists
print("\nChecking for LINKEDIN_JOBS table...")
cursor.execute("SHOW TABLES LIKE 'LINKEDIN_JOBS'")
tables = cursor.fetchall()
if tables:
    print(f"✓ Table exists: {tables[0]}")
else:
    print("✗ Table LINKEDIN_JOBS does not exist")
    conn.close()
    exit(1)

# Count total records
cursor.execute("SELECT COUNT(*) FROM LINKEDIN_JOBS")
total = cursor.fetchone()[0]
print(f"\n✓ Total records in LINKEDIN_JOBS: {total}")

# Check for test records
cursor.execute("""
    SELECT COUNT(*) FROM LINKEDIN_JOBS
    WHERE SEARCH_QUERY LIKE 'cdc%' OR SEARCH_QUERY LIKE 'realtime%'
""")
test_count = cursor.fetchone()[0]
print(f"✓ Test CDC records: {test_count}")

# Show recent test records
if test_count > 0:
    print("\nRecent test records:")
    cursor.execute("""
        SELECT JOB_ID, JOB_TITLE, COMPANY_NAME, SEARCH_QUERY, _CDC_OPERATION
        FROM LINKEDIN_JOBS
        WHERE SEARCH_QUERY LIKE 'cdc%' OR SEARCH_QUERY LIKE 'realtime%'
        ORDER BY JOB_ID DESC
        LIMIT 10
    """)

    for row in cursor.fetchall():
        print(f"  - {row[0]}: {row[1]} at {row[2]} (search: {row[3]}, op: {row[4]})")

# Show CDC metadata columns
print("\nSample CDC metadata:")
cursor.execute("""
    SELECT JOB_ID, _CDC_OPERATION, _CDC_TIMESTAMP, _CDC_SOURCE_LSN
    FROM LINKEDIN_JOBS
    WHERE _CDC_OPERATION IS NOT NULL
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"  - {row[0]}: op={row[1]}, ts={row[2]}, lsn={row[3]}")

conn.close()
print("\n✓ Snowflake verification complete!")
