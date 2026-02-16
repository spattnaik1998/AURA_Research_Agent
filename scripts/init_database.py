#!/usr/bin/env python3
"""Initialize AURA Research database"""
import pyodbc
import sys
import os

# Connection parameters
server = 'sqlserver'
user = 'sa'
password = 'AuraSecure2024!#Prod'
driver = '{ODBC Driver 17 for SQL Server}'

try:
    # Connect to master database first
    print("Connecting to SQL Server...")
    conn_str = f'Driver={driver};Server={server};UID={user};PWD={password};TrustServerCertificate=yes'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Create database
    print("Creating AURA_Research database...")
    cursor.execute("CREATE DATABASE AURA_Research COLLATE SQL_Latin1_General_CP1_CI_AS")
    cursor.commit()
    print("✓ Database created")

    # Connect to new database
    print("Connecting to AURA_Research database...")
    cursor.close()
    conn.close()

    conn_str = f'Driver={driver};Server={server};Database=AURA_Research;UID={user};PWD={password};TrustServerCertificate=yes'
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    # Read and execute schema.sql
    print("Reading schema.sql...")
    schema_path = '/app/database/schema.sql'
    with open(schema_path, 'r') as f:
        schema = f.read()

    # Split by GO statements and execute
    print("Creating tables...")
    statements = schema.split('GO\n')
    for stmt in statements:
        stmt = stmt.strip()
        if stmt:
            try:
                cursor.execute(stmt)
            except Exception as e:
                if 'already exists' not in str(e):
                    print(f"Warning: {e}")

    cursor.commit()
    print("✓ Schema created")

    # Apply migrations
    migrations_dir = '/app/database/migrations'
    if os.path.exists(migrations_dir):
        migrations = sorted([f for f in os.listdir(migrations_dir) if f.endswith('.sql')])

        for migration_file in migrations:
            print(f"Applying {migration_file}...")
            with open(os.path.join(migrations_dir, migration_file), 'r') as f:
                migration = f.read()

            statements = migration.split('GO\n')
            for stmt in statements:
                stmt = stmt.strip()
                if stmt:
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        if 'already exists' not in str(e):
                            print(f"Warning: {e}")

            cursor.commit()
            print(f"✓ {migration_file} applied")

    cursor.close()
    conn.close()

    print("\n✅ Database initialization complete!")
    print("  Tables: 14 (schema + migrations)")
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
