#!/bin/bash
# Setup SQL Server with initial schema (if using external SQL Server)

DB_SERVER=${DB_SERVER:-"localhost"}
DB_USER=${DB_USERNAME:-"sa"}
DB_PASS=${DB_PASSWORD}

echo "Setting up AURA_Research database..."

# Create database
sqlcmd -S $DB_SERVER -U $DB_USER -P $DB_PASS -Q "CREATE DATABASE AURA_Research"

# Run schema
sqlcmd -S $DB_SERVER -U $DB_USER -P $DB_PASS -d AURA_Research -i database/schema.sql

# Run migrations
for migration in database/migrations/*.sql; do
    echo "Running: $migration"
    sqlcmd -S $DB_SERVER -U $DB_USER -P $DB_PASS -d AURA_Research -i "$migration"
done

echo "Database setup complete!"
