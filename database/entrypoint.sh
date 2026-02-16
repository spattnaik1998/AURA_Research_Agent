#!/bin/bash
set -e

# AURA Research Agent - SQL Server Database Initialization Script
# This script runs when the SQL Server container starts for the first time
# It automatically creates the database, schema, and applies all migrations

echo "=========================================="
echo "AURA Research Agent - Database Setup"
echo "=========================================="

# Wait for SQL Server to be ready to accept connections
echo "[1/5] Waiting for SQL Server to start..."
for i in {1..50}; do
    if /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${SA_PASSWORD}" -Q "SELECT 1" -C &> /dev/null; then
        echo "✓ SQL Server is ready"
        break
    fi
    if [ $i -eq 50 ]; then
        echo "✗ SQL Server failed to start after 100 seconds"
        exit 1
    fi
    sleep 2
done

# Check if AURA_Research database already exists
echo "[2/5] Checking database status..."
DB_EXISTS=$(/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${SA_PASSWORD}" \
    -Q "SELECT COUNT(*) FROM sys.databases WHERE name='AURA_Research'" -h -1 -C 2>/dev/null | tr -d '[:space:]')

if [ "$DB_EXISTS" = "0" ]; then
    echo "✓ AURA_Research database does not exist - initializing..."

    # Create the database with proper collation
    echo "[3/5] Creating AURA_Research database..."
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${SA_PASSWORD}" \
        -Q "CREATE DATABASE AURA_Research COLLATE SQL_Latin1_General_CP1_CI_AS" -C

    # Run schema.sql to create tables and initial structure
    echo "[4/5] Running database schema..."
    if [ -f /docker-entrypoint-initdb.d/schema.sql ]; then
        /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${SA_PASSWORD}" \
            -d AURA_Research \
            -i /docker-entrypoint-initdb.d/schema.sql -C
        echo "✓ Schema created successfully"
    else
        echo "⚠ Warning: schema.sql not found at /docker-entrypoint-initdb.d/schema.sql"
    fi

    # Run all migrations in order (001, 002, 003, 004, etc.)
    echo "[5/5] Running migrations..."
    MIGRATION_COUNT=0
    for migration in /docker-entrypoint-initdb.d/migrations/*.sql; do
        if [ -f "$migration" ]; then
            MIGRATION_NAME=$(basename "$migration")
            echo "  → Applying $MIGRATION_NAME..."
            /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "${SA_PASSWORD}" \
                -d AURA_Research \
                -i "$migration" -C
            MIGRATION_COUNT=$((MIGRATION_COUNT + 1))
        fi
    done

    if [ $MIGRATION_COUNT -eq 0 ]; then
        echo "⚠ No migrations found at /docker-entrypoint-initdb.d/migrations/"
    else
        echo "✓ Applied $MIGRATION_COUNT migrations"
    fi

    echo ""
    echo "=========================================="
    echo "✓ Database initialization complete!"
    echo "=========================================="
    echo "Database: AURA_Research"
    echo "Tables: $(($MIGRATION_COUNT + 1)) (schema + migrations)"
    echo "Ready for application use"
    echo ""

else
    echo "✓ AURA_Research database exists"
    echo "  Skipping initialization (database already initialized)"
fi

# Start SQL Server and keep it running
echo "Starting SQL Server..."
exec /opt/mssql/bin/sqlservr
