#!/bin/bash
# Initialize database schema in Docker SQL Server

# Wait for SQL Server to be ready
sleep 30

# Run schema creation
/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P ${SA_PASSWORD} -d master -i /docker-entrypoint-initdb.d/schema.sql -C

# Run migrations
for migration in /docker-entrypoint-initdb.d/migrations/*.sql; do
    echo "Running migration: $migration"
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P ${SA_PASSWORD} -d AURA_Research -i "$migration" -C
done

echo "Database initialization complete"
