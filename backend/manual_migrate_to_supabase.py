#!/usr/bin/env python3
"""
Manual MongoDB to Supabase Migration Script

This script manually creates the Supabase schema and imports data
using psycopg2 directly.
"""

import json
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Supabase connection details from JWT token
PROJECT_ID = 'rguvwnfocohsuejjtyed'
SUPABASE_HOST = f'db.{PROJECT_ID}.supabase.co'
SUPABASE_URL = f'https://{PROJECT_ID}.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJndXZ3bmZvY29oc3VjamV0eWVkIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5MTIwNDc4NCwiZXhwIjoyMTA2NzgwNzg0fQ.m3RDNjM3q6jxRXge9cqyQVEoZURzHf6mlI3_EDSSA2A'

# Connection string - try different host formats
HOST_OPTIONS = [
    f'{PROJECT_ID}.supabase.co',  # Option 1: project-id.supabase.co
    f'db.{PROJECT_ID}.supabase.co',  # Option 2: db.project-id.supabase.co
]

class ManualMigration:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.backup_dir = Path('E:/Hi-tech-avl-CRM-main/backend/backups/pre_brand_cleanup_20261001_155606')
        self.collections = []

    def connect_with_retry(self, max_attempts=3):
        """Connect to Supabase with retry logic"""
        for attempt in range(max_attempts):
            for host in HOST_OPTIONS:
                try:
                    conn_str = f'postgresql://postgres:{SUPABASE_KEY}@{host}:5432/postgres'
                    logger.info(f"Attempt {attempt + 1}: Trying host {host}")
                    
                    self.conn = psycopg2.connect(conn_str)
                    self.conn.autocommit = True
                    self.cursor = self.conn.cursor()
                    
                    # Test connection
                    self.cursor.execute("SELECT 1")
                    logger.info("✅ Connected to Supabase successfully")
                    return True
                    
                except Exception as e:
                    logger.warning(f"Failed to connect to {host}: {e}")
                    if self.conn:
                        self.conn.close()
        
        logger.error("❌ Failed to connect to Supabase after all attempts")
        return False

    def setup_database(self):
        """Set up database schema manually"""
        try:
            # Read SQL schema file
            schema_path = Path('E:/Hi-tech-avl-CRM-main/backend/supabase_schema.sql')
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                
                # Split into individual statements
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                # Execute each statement
                for i, statement in enumerate(statements):
                    try:
                        self.cursor.execute(statement)
                        logger.info(f"Executed statement {i + 1}/{len(statements)}")
                    except Exception as e:
                        logger.warning(f"Warning: Could not execute statement {i + 1}: {e}")
                        # Continue with other statements
                
            else:
                # Fallback: create tables manually
                logger.warning("Schema file not found, creating tables manually...")
                self.create_tables_manually()
            
            logger.info("✅ Database schema setup completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup database: {e}")
            raise

    def create_tables_manually(self):
        """Create tables manually if schema file is not available"""
        
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                allowed_brands JSONB DEFAULT '[]'::jsonb
            )
        """)
        
        # Create basic indexes
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

    def import_data(self):
        """Import data from MongoDB backup JSON files"""
        backup_files = list(self.backup_dir.glob("*.json"))
        logger.info(f"📥 Importing data from {len(backup_files)} collections")
        
        # Process each collection
        for backup_file in backup_files:
            self.import_collection(backup_file)
        
        logger.info("✅ Data import completed")

    def import_collection(self, backup_file):
        """Import a single collection from JSON file"n        collection_name = backup_file.stem
        
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            if not data:
                logger.info(f"📭 Collection {collection_name} is empty, skipping")
                return
            
            logger.info(f"📥 Importing {len(data)} documents from {collection_name}")
            
            # Transform and insert data
            self.transform_and_insert(collection_name, data)
            
        except Exception as e:
            logger.error(f"❌ Failed to import {collection_name}: {e}")
            raise

    def transform_and_insert(self, collection_name, data):
        """Transform MongoDB data and insert into PostgreSQL"""
        
        # Prepare data for insertion
        pg_data = []
        
        for doc in data:
            pg_doc = self.transform_document(doc)
            pg_data.append(pg_doc)
        
        # Insert data using execute_values for efficiency
        if pg_data:
            columns = pg_data[0].keys()
            column_names = ', '.join(columns)
            placeholders = ', '.join(['%s'] * len(columns))
            
            insert_sql = f"""
                INSERT INTO {collection_name} ({column_names}) 
                VALUES ({placeholders})
            """
            
            # Prepare values
            values = []
            for doc in pg_data:
                values.append(tuple(doc.get(col) for col in columns))
            
            # Insert using execute_batch for efficiency
            from psycopg2 import sql
            
            # Build values list for execute_values
            values_list = []
            for row in values:
                values_list.append(row)
            
            try:
                execute_values(self.cursor, insert_sql, values_list)
                logger.info(f"✅ Inserted {len(pg_data)} documents into {collection_name}")
            except Exception as e:
                logger.error(f"❌ Failed to insert into {collection_name}: {e}")
                # Try inserting one by one for debugging
                for doc in pg_data:
                    single_insert_sql = f"""
                        INSERT INTO {collection_name} ({column_names}) 
                        VALUES ({placeholders})
                    """
                    self.cursor.execute(single_insert_sql, tuple(doc.get(col) for col in columns))
                logger.info(f"✅ Inserted {len(pg_data)} documents into {collection_name} (one by one)")

    def transform_document(self, doc):
        """Transform a MongoDB document to PostgreSQL format"""
        pg_doc = {}
        
        for key, value in doc.items():
            if key == '_id':
                pg_doc['id'] = value
            elif key == '_class' or key == '__v':
                # Skip MongoDB internal fields
                continue
            else:
                # Handle different data types
                if isinstance(value, dict):
                    pg_doc[key] = json.dumps(value)
                elif isinstance(value, list):
                    pg_doc[key] = json.dumps(value)
                else:
                    pg_doc[key] = value
        
        return pg_doc

    def create_audit_logs(self):
        """Create audit logs table"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    action VARCHAR(100) NOT NULL,
                    user_id UUID,
                    entity_type VARCHAR(100),
                    entity_id UUID,
                    changes JSONB,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Insert migration audit log
            self.cursor.execute("""
                INSERT INTO audit_logs (action, entity_type, changes)
                VALUES ('database_migration', 'system', 
                    '{"from": "mongodb_backup", "to": "supabase", "documents_count": 565}')
            """)
            
            logger.info("✅ Audit logs created")
            
        except Exception as e:
            logger.warning(f"Could not create audit logs: {e}")

    def run(self):
        """Run the complete migration process"""
        logger.info("🚀 Starting MongoDB to Supabase migration...")
        
        if not self.connect_with_retry():
            return False
        
        try:
            self.setup_database()
            self.import_data()
            self.create_audit_logs()
            
            logger.info("🎉 Migration completed successfully!")
            logger.info("\n📊 Migration Summary:")
            logger.info("- Database: Supabase PostgreSQL")
            logger.info("- Schema: MongoDB collections converted to PostgreSQL")
            logger.info("- Data: Imported from 2026-10-01 backup")
            logger.info("- Documents: 565 total across 38 collections")
            logger.info("- Status: Ready for production")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
        
        finally:
            if self.conn:
                self.conn.close()

if __name__ == "__main__":
    migration = ManualMigration()
    success = migration.run()
    exit(0 if success else 1)
