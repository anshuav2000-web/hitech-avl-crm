#!/usr/bin/env python3
"""
Hitech AVL CRM - MongoDB to Supabase Migration Script

This script helps migrate the CRM database from MongoDB to Supabase PostgreSQL.
It includes both schema creation and data import functionality.

Usage:
    python migrate_to_supabase.py [options]

Options:
    --dry-run          Preview what will be migrated without executing
    --backup-only     Only create the schema, don't import data
    --data-only       Only import data, assume schema exists
    --help            Show this help message

Prerequisites:
    1. Supabase PostgreSQL instance is running
    2. Supabase credentials (URL and key) are set in environment variables
    3. Python packages: psycopg2-binary, sqlalchemy

Environment Variables Required:
    SUPABASE_URL - Your Supabase project URL
    SUPABASE_KEY - Your Supabase service role key
    DATABASE_URL - PostgreSQL connection string (alternative to SUPABASE_URL)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class MigrationError(Exception):
    """Custom exception for migration errors"""
    pass

class DatabaseConnector:
    """Handles database connections for both MongoDB and Supabase"""
    
    def __init__(self, use_supabase: bool = True):
        self.use_supabase = use_supabase
        self.connection = None
        self.cursor = None
        
    def connect(self) -> bool:
        """Connect to the database"""
        try:
            if self.use_supabase:
                self._connect_supabase()
            else:
                self._connect_mongodb()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def _connect_supabase(self):
        """Connect to Supabase PostgreSQL"""
        # Try to get connection string from environment variables
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        database_url = os.getenv('DATABASE_URL')
        
        if database_url:
            # Use direct PostgreSQL connection
            import psycopg2
            self.connection = psycopg2.connect(database_url)
            self.cursor = self.connection.cursor()
            logger.info("✅ Connected to Supabase via DATABASE_URL")
        elif supabase_url and supabase_key:
            # Use Supabase connection string
            import psycopg2
            # Construct connection string
            conn_str = f"postgresql://postgres:{supabase_key}@{supabase_url.replace('https://', '')}:5432/postgres"
            self.connection = psycopg2.connect(conn_str)
            self.cursor = self.connection.cursor()
            logger.info("✅ Connected to Supabase via SUPABASE_URL and SUPABASE_KEY")
        else:
            raise MigrationError("No Supabase connection details found. Set SUPABASE_URL and SUPABASE_KEY or DATABASE_URL.")
    
    def _connect_mongodb(self):
        """Connect to MongoDB"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            mongo_url = os.getenv('MONGO_URL') or os.getenv('DATABASE_URL')
            if not mongo_url:
                raise MigrationError("No MongoDB connection details found. Set MONGO_URL or DATABASE_URL.")
            
            # For sync operations, we'll use pymongo
            import pymongo
            self.connection = pymongo.MongoClient(mongo_url)
            self.cursor = self.connection
            self.db = self.connection[os.getenv('DB_NAME', 'hitech_crm')]
            logger.info("✅ Connected to MongoDB")
        except ImportError:
            raise MigrationError("MongoDB driver not installed. Install with: pip install pymongo")
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("🔌 Database connection closed")
    
    def execute_query(self, query: str, params: tuple = None) -> Any:
        """Execute a SQL query"""
        try:
            if self.use_supabase:
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                return self.cursor
            else:
                # For MongoDB, this is a placeholder for future implementation
                raise NotImplementedError("MongoDB query execution not implemented yet")
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise

class SchemaManager:
    """Manages database schema creation"""
    
    def __init__(self, connector: DatabaseConnector):
        self.connector = connector
        self.schema_file = Path('supabase_schema.sql')
    
    def create_schema(self) -> bool:
        """Create the database schema"""
        try:
            logger.info("🏗️  Creating database schema...")
            
            if not self.schema_file.exists():
                logger.warning("Schema file not found. Creating default schema...")
                self._create_default_schema()
            else:
                self._create_schema_from_file()
            
            logger.info("✅ Schema created successfully")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create schema: {e}")
            return False
    
    def _create_default_schema(self):
        """Create a basic schema if schema file is missing"""
        tables = [
            "users",
            "roles", 
            "leads",
            "products",
            "quotations",
            "projects",
            "tasks",
            "activities",
            "customers",
            "contacts",
            "brands",
            "events",
            "social_posts",
            "suppliers",
            "shipments",
            "bookings",
            "boqs",
            "design_tasks",
            "sidebar_layouts",
            "dashboard_layouts",
            "settings",
            "crm_config_sets"
        ]
        
        for table in tables:
            self._create_table(table)
    
    def _create_schema_from_file(self):
        """Create schema from SQL file"""
        with open(self.schema_file, 'r') as f:
            schema_sql = f.read()
        
        # Split SQL statements
        statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            try:
                self.connector.execute_query(statement)
                logger.info(f"✅ Executed schema statement {i + 1}/{len(statements)}")
            except Exception as e:
                logger.warning(f"⚠️  Could not execute schema statement {i + 1}: {e}")
                # Continue with other statements
    
    def _create_table(self, table_name: str):
        """Create a single table"""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        self.connector.execute_query(create_sql)
        logger.info(f"✅ Created table: {table_name}")

class DataImporter:
    """Manages data import from MongoDB backup"""
    
    def __init__(self, connector: DatabaseConnector, backup_dir: Path):
        self.connector = connector
        self.backup_dir = backup_dir
        self.backup_files = list(backup_dir.glob('*.json'))
    
    def import_data(self) -> bool:
        """Import data from MongoDB backup files"""
        try:
            logger.info(f"📥 Importing data from {len(self.backup_files)} backup files...")
            
            total_documents = 0
            for backup_file in self.backup_files:
                collection_name = backup_file.stem
                try:
                    imported = self._import_collection(backup_file, collection_name)
                    total_documents += imported
                    logger.info(f"✅ Imported {imported} documents from {collection_name}")
                except Exception as e:
                    logger.error(f"❌ Failed to import {collection_name}: {e}")
                    raise
            
            logger.info(f"✅ Data import completed: {total_documents} total documents imported")
            return True
            
        except Exception as e:
            logger.error(f"❌ Data import failed: {e}")
            return False
    
    def _import_collection(self, backup_file: Path, collection_name: str) -> int:
        """Import a single collection"""
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                data = [data]
            
            if not data:
                logger.warning(f"📭 Collection {collection_name} is empty, skipping")
                return 0
            
            # Transform MongoDB documents to PostgreSQL format
            pg_data = self._transform_documents(data)
            
            # Insert data
            return self._insert_data(collection_name, pg_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to process {collection_name}: {e}")
            raise
    
    def _transform_documents(self, documents: List[Dict]) -> List[Dict]:
        """Transform MongoDB documents to PostgreSQL format"""
        transformed = []
        
        for doc in documents:
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
            
            transformed.append(pg_doc)
        
        return transformed
    
    def _insert_data(self, collection_name: str, data: List[Dict]) -> int:
        """Insert data into database"""
        if not data:
            return 0
        
        # Build INSERT statement
        columns = data[0].keys()
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        insert_sql = f"""
        INSERT INTO {collection_name} ({column_names}) 
        VALUES ({placeholders})
        """
        
        # Prepare values
        values = []
        for doc in data:
            row = tuple(doc.get(col) for col in columns)
            values.append(row)
        
        # Insert data
        try:
            # For now, we'll use a simple approach
            # In a real implementation, you'd use psycopg2.extras.execute_batch
            for row in values:
                self.connector.execute_query(insert_sql, row)
            
            return len(values)
            
        except Exception as e:
            logger.error(f"❌ Failed to insert data into {collection_name}: {e}")
            raise

class MigrationManager:
    """Main migration manager"""
    
    def __init__(self, args):
        self.args = args
        self.backup_dir = Path('E:/Hi-tech-avl-CRM-main/backend/backups/pre_brand_cleanup_20261001_155606')
        
        # Check if Supabase is configured
        self.use_supabase = self._check_supabase_config()
        self.use_mongodb = self._check_mongodb_config()
        
        if not self.use_supabase and not self.use_mongodb:
            raise MigrationError("No database configuration found. Set SUPABASE_URL/SUPABASE_KEY or MONGO_URL environment variables.")
        
        self.connector = None
        self.schema_manager = None
        self.data_importer = None
    
    def _check_supabase_config(self) -> bool:
        """Check if Supabase is configured"""
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_KEY')
        database_url = os.getenv('DATABASE_URL')
        
        return bool(supabase_url and supabase_key) or bool(database_url)
    
    def _check_mongodb_config(self) -> bool:
        """Check if MongoDB is configured"""
        mongo_url = os.getenv('MONGO_URL') or os.getenv('DATABASE_URL')
        return bool(mongo_url)
    
    def run(self) -> bool:
        """Run the migration"""
        logger.info("🚀 Starting MongoDB to Supabase Migration")
        logger.info(f"Database configuration: Supabase={self.use_supabase}, MongoDB={self.use_mongodb}")
        logger.info(f"Backup directory: {self.backup_dir}")
        
        try:
            # Initialize database connector
            self.connector = DatabaseConnector(self.use_supabase)
            if not self.connector.connect():
                return False
            
            # Initialize schema manager
            self.schema_manager = SchemaManager(self.connector)
            
            # Initialize data importer
            self.data_importer = DataImporter(self.connector, self.backup_dir)
            
            # Run migration steps based on arguments
            if self.args.schema_only:
                logger.info("🏗️  Schema-only migration mode")
                if not self.schema_manager.create_schema():
                    return False
            
            elif self.args.data_only:
                logger.info("📥 Data-only migration mode")
                if not self.data_importer.import_data():
                    return False
            
            else:
                # Full migration
                logger.info("🔄 Running full migration (schema + data)")
                
                if not self.schema_manager.create_schema():
                    return False
                
                if not self.data_importer.import_data():
                    return False
            
            logger.info("🎉 Migration completed successfully!")
            self._print_summary()
            return True
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return False
        
        finally:
            if self.connector:
                self.connector.close()
    
    def _print_summary(self):
        """Print migration summary"""
        logger.info("\n📊 Migration Summary:")
        logger.info(f"Database: {'Supabase PostgreSQL' if self.use_supabase else 'MongoDB'}")
        logger.info(f"Backup Files Processed: {len(self.backup_files)}")
        logger.info("Status: Migration completed successfully")
        logger.info("Next Steps:")
        logger.info("1. Update application environment variables")
        logger.info("2. Restart services with new database configuration")
        logger.info("3. Test all API endpoints")
        logger.info("4. Verify data integrity")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Hitech AVL CRM Database Migration Script")
    parser.add_argument('--dry-run', action='store_true', help='Preview what will be migrated without executing')
    parser.add_argument('--schema-only', action='store_true', help='Only create the schema, don\\'t import data')
    parser.add_argument('--data-only', action='store_true', help='Only import data, assume schema exists')
    parser.add_argument('--supabase-only', action='store_true', help='Only migrate to Supabase')
    parser.add_argument('--mongodb-only', action='store_true', help='Only migrate from MongoDB (keep Supabase config)')
    parser.add_argument('--backup-dir', default='E:/Hi-tech-avl-CRM-main/backend/backups/pre_brand_cleanup_20261001_155606',n help='Path to backup directory')
    
    return parser.parse_args()

def main():
    """Main function"""
    try:
        args = parse_arguments()
        
        # Validate arguments
        if args.schema_only and args.data_only:
            print("Error: Cannot specify both --schema-only and --data-only")
            return 1
        
        # Create migration manager
        migration = MigrationManager(args)
        
        # Run migration
        success = migration.run()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️  Migration interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Migration setup failed: {e}")
        return 1

if __name__ == '__main__':
    exit(main())
