#!/usr/bin/env python3
"""
Database Adapter for Hitech AVL CRM

This module provides a unified interface for database operations,
supporting both MongoDB (legacy) and Supabase (new).

Usage:
- Set SUPABASE_URL and SUPABASE_KEY environment variables for Supabase
- Set MONGO_URL environment variable for MongoDB (legacy)
- The adapter will automatically use Supabase if available, otherwise MongoDB
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseAdapter:
    """Database adapter supporting both Supabase PostgreSQL and MongoDB"""
    
    def __init__(self):
        self.use_supabase = self._check_supabase_available()
        self.use_mongodb = self._check_mongodb_available()
        
        if not self.use_supabase and not self.use_mongodb:
            raise RuntimeError("No database configured. Set SUPABASE_URL/SUPABASE_KEY or MONGO_URL environment variables.")
        
        if self.use_supabase:
            self._init_supabase()
        elif self.use_mongodb:
            self._init_mongodb()
        
        logger.info(f"Database initialized: {'Supabase' if self.use_supabase else 'MongoDB' if self.use_mongodb else 'None'}")

    def _check_supabase_available(self) -> bool:
        """Check if Supabase is configured and available"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        return bool(supabase_url and supabase_key)

    def _check_mongodb_available(self) -> bool:
        """Check if MongoDB is configured and available"""
        mongo_url = os.getenv("MONGO_URL") or os.getenv("DATABASE_URL")
        return bool(mongo_url)

    def _init_supabase(self):
        """Initialize Supabase connection"""
        try:
            from supabase import create_client, Client
            
            self.supabase_url = os.getenv("SUPABASE_URL")
            self.supabase_key = os.getenv("SUPABASE_KEY")
            
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("✅ Supabase client initialized successfully")
            
        except ImportError:
            logger.error("❌ Supabase package not installed. Install with: pip install supabase")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")
            raise

    def _init_mongodb(self):
        """Initialize MongoDB connection"""
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_url = os.getenv("MONGO_URL") or os.getenv("DATABASE_URL")
            self.mongo_client = AsyncIOMotorClient(mongo_url)
            self.mongo_db = self.mongo_client[os.getenv("DB_NAME", "hitech_crm")]
            
            logger.info("✅ MongoDB client initialized successfully")
            
        except ImportError:
            logger.error("❌ Motor package not installed. Install with: pip install motor")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to initialize MongoDB client: {e}")
            raise

    # Generic CRUD operations
    
    async def find(self, collection: str, query: Dict = None, limit: int = None, sort: Dict = None) -> List[Dict]:
        """Find documents in collection"""
        if self.use_supabase:
            return await self._supabase_find(collection, query, limit, sort)
        elif self.use_mongodb:
            return await self._mongodb_find(collection, query, limit, sort)
        else:
            return []

    async def find_one(self, collection: str, query: Dict = None) -> Optional[Dict]:
        """Find single document in collection"""
        if self.use_supabase:
            return await self._supabase_find_one(collection, query)
        elif self.use_mongodb:
            return await self._mongodb_find_one(collection, query)
        else:
            return None

    async def insert_one(self, collection: str, document: Dict) -> Dict:
        """Insert single document in collection"""
        if self.use_supabase:
            return await self._supabase_insert_one(collection, document)
        elif self.use_mongodb:
            return await self._mongodb_insert_one(collection, document)
        else:
            return {}

    async def insert_many(self, collection: str, documents: List[Dict]) -> List[Dict]:
        """Insert multiple documents in collection"""
        if self.use_supabase:
            return await self._supabase_insert_many(collection, documents)
        elif self.use_mongodb:
            return await self._mongodb_insert_many(collection, documents)
        else:
            return []

    async def update_one(self, collection: str, query: Dict, update: Dict, upsert: bool = False) -> Dict:
        """Update single document in collection"""
        if self.use_supabase:
            return await self._supabase_update_one(collection, query, update, upsert)
        elif self.use_mongodb:
            return await self._mongodb_update_one(collection, query, update, upsert)
        else:
            return {}

    async def delete_one(self, collection: str, query: Dict) -> Dict:
        """Delete single document in collection"""
        if self.use_supabase:
            return await self._supabase_delete_one(collection, query)
        elif self.use_mongodb:
            return await self._mongodb_delete_one(collection, query)
        else:
            return {}

    async def count(self, collection: str, query: Dict = None) -> int:
        """Count documents in collection"""
        if self.use_supabase:
            return await self._supabase_count(collection, query)
        elif self.use_mongodb:
            return await self._mongodb_count(collection, query)
        else:
            return 0

    # Supabase-specific operations
    
    async def _supabase_find(self, collection: str, query: Dict = None, limit: int = None, sort: Dict = None) -> List[Dict]:
        """Find documents in Supabase"""
        try:
            supabase_query = self._transform_query_for_supabase(query)
            
            if limit:
                supabase_query = supabase_query.limit(limit)
            
            if sort:
                supabase_query = self._transform_sort_for_supabase(sort)
            
            response = supabase_query.execute()
            
            if response.data:
                return response.data
            return []
            
        except Exception as e:
            logger.error(f"❌ Supabase find failed: {e}")
            raise

    async def _supabase_find_one(self, collection: str, query: Dict = None) -> Optional[Dict]:
        """Find single document in Supabase"""
        try:
            supabase_query = self._transform_query_for_supabase(query)
            response = supabase_query.single().execute()
            
            return response.data if response.data else None
            
        except Exception as e:
            logger.error(f"❌ Supabase find_one failed: {e}")
            raise

    async def _supabase_insert_one(self, collection: str, document: Dict) -> Dict:
        """Insert single document in Supabase"""
        try:
            # Convert document to Supabase format
            supabase_document = self._transform_document_for_supabase(document)
            
            response = self.supabase.table(collection).insert(supabase_document).execute()
            
            return response.data[0] if response.data else {}
            
        except Exception as e:
            logger.error(f"❌ Supabase insert_one failed: {e}")
            raise

    async def _supabase_insert_many(self, collection: str, documents: List[Dict]) -> List[Dict]:
        """Insert multiple documents in Supabase"""
        try:
            # Transform all documents
            supabase_documents = [self._transform_document_for_supabase(doc) for doc in documents]
            
            response = self.supabase.table(collection).insert(supabase_documents).execute()
            
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"❌ Supabase insert_many failed: {e}")
            raise

    async def _supabase_update_one(self, collection: str, query: Dict, update: Dict, upsert: bool = False) -> Dict:
        """Update single document in Supabase"""
        try:
            supabase_query = self._transform_query_for_supabase(query)
            supabase_update = self._transform_update_for_supabase(update)
            
            if upsert:
                response = supabase_query.upsert(supabase_update).execute()
            else:
                response = supabase_query.update(supabase_update).execute()
            
            return response.data[0] if response.data else {}
            
        except Exception as e:
            logger.error(f"❌ Supabase update_one failed: {e}")
            raise

    async def _supabase_delete_one(self, collection: str, query: Dict) -> Dict:
        """Delete single document in Supabase"""
        try:
            supabase_query = self._transform_query_for_supabase(query)
            response = supabase_query.delete().execute()
            
            return {"message": "Document deleted"} if response.data else {}
            
        except Exception as e:
            logger.error(f"❌ Supabase delete_one failed: {e}")
            raise

    async def _supabase_count(self, collection: str, query: Dict = None) -> int:
        """Count documents in Supabase"""
        try:
            supabase_query = self._transform_query_for_supabase(query)
            response = supabase_query.select("count").execute()
            
            if response.count:
                return int(response.count)
            return 0
            
        except Exception as e:
            logger.error(f"❌ Supabase count failed: {e}")
            raise

    # MongoDB-specific operations
    
    async def _mongodb_find(self, collection: str, query: Dict = None, limit: int = None, sort: Dict = None) -> List[Dict]:
        """Find documents in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            cursor = mongo_collection.find(query or {})
            
            if sort:
                cursor = cursor.sort(sort)
            
            if limit:
                cursor = cursor.limit(limit)
            
            documents = await cursor.to_list(length=None)
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ MongoDB find failed: {e}")
            raise

    async def _mongodb_find_one(self, collection: str, query: Dict = None) -> Optional[Dict]:
        """Find single document in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            document = await mongo_collection.find_one(query or {})
            
            return document
            
        except Exception as e:
            logger.error(f"❌ MongoDB find_one failed: {e}")
            raise

    async def _mongodb_insert_one(self, collection: str, document: Dict) -> Dict:
        """Insert single document in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            result = await mongo_collection.insert_one(document)
            
            # Get the inserted document
            inserted_document = await mongo_collection.find_one({"_id": result.inserted_id})
            
            return inserted_document
            
        except Exception as e:
            logger.error(f"❌ MongoDB insert_one failed: {e}")
            raise

    async def _mongodb_insert_many(self, collection: str, documents: List[Dict]) -> List[Dict]:
        """Insert multiple documents in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            result = await mongo_collection.insert_many(documents)
            
            # Get the inserted documents
            inserted_ids = result.inserted_ids
            documents = []
            
            for doc_id in inserted_ids:
                doc = await mongo_collection.find_one({"_id": doc_id})
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"❌ MongoDB insert_many failed: {e}")
            raise

    async def _mongodb_update_one(self, collection: str, query: Dict, update: Dict, upsert: bool = False) -> Dict:
        """Update single document in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            update_operation = {"$set": update} if not upsert else update
            
            result = await mongo_collection.update_one(
                query, 
                update_operation, 
                upsert=upsert
            )
            
            # Get the updated document
            updated_document = await mongo_collection.find_one(query)
            
            return updated_document
            
        except Exception as e:
            logger.error(f"❌ MongoDB update_one failed: {e}")
            raise

    async def _mongodb_delete_one(self, collection: str, query: Dict) -> Dict:
        """Delete single document in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            result = await mongo_collection.delete_one(query)
            
            return {"message": "Document deleted"}
            
        except Exception as e:
            logger.error(f"❌ MongoDB delete_one failed: {e}")
            raise

    async def _mongodb_count(self, collection: str, query: Dict = None) -> int:
        """Count documents in MongoDB"""
        try:
            mongo_collection = self.mongo_db[collection]
            
            count = await mongo_collection.count_documents(query or {})
            
            return count
            
        except Exception as e:
            logger.error(f"❌ MongoDB count failed: {e}")
            raise

    # Query transformation methods
    
    def _transform_query_for_supabase(self, query: Dict = None) -> Any:
        """Transform MongoDB query to Supabase query"""
        if not query:
            return self.supabase.table("temp")  # Placeholder
        
        # For now, return a simple Supabase query
        # In production, you'd implement proper transformation
        supabase_query = self.supabase.table("temp")
        
        return supabase_query

    def _transform_sort_for_supabase(self, sort: Dict) -> Any:
        """Transform MongoDB sort to Supabase sort"""
        # Implement sort transformation
        return self.supabase.table("temp")

    def _transform_document_for_supabase(self, document: Dict) -> Dict:
        """Transform MongoDB document to Supabase document"""
        # Remove MongoDB-specific fields
        transformed = document.copy()
        
        if '_id' in transformed:
            transformed['id'] = transformed['_id']
            del transformed['_id']
        
        if '__v' in transformed:
            del transformed['__v']
        
        # Transform nested documents
        for key, value in transformed.items():
            if isinstance(value, dict) and '_id' in value:
                # Convert nested object with _id to id
                nested = value.copy()
                if '_id' in nested:
                    nested['id'] = nested['_id']
                    del nested['_id']
                transformed[key] = nested
        
        return transformed

    def _transform_update_for_supabase(self, update: Dict) -> Dict:
        """Transform MongoDB update to Supabase update"""
        # Convert MongoDB update operator ($set, $inc, etc.) to Supabase format
        transformed = {}
        
        for operator, fields in update.items():
            if operator == '$set':
                for field, value in fields.items():
                    transformed[field] = value
            elif operator == '$inc':
                for field, value in fields.items():
                    transformed[field] = f"{value}+1"  # Simplified
            else:
                # Handle other operators as needed
                transformed.update(fields)
        
        return transformed

    def get_status(self) -> Dict:
        """Get database connection status"""
        return {
            "supabase": self.use_supabase,
            "supabase_url": self.supabase_url if self.use_supabase else None,
            "mongodb": self.use_mongodb,
            "mongo_url": os.getenv("MONGO_URL") or os.getenv("DATABASE_URL") if self.use_mongodb else None,
            "active_database": "supabase" if self.use_supabase else "mongodb" if self.use_mongodb else "none"
        }

# Singleton instance
_db_instance = None

async def get_db() -> DatabaseAdapter:
    """Get database adapter instance (singleton)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseAdapter()
    return _db_instance

async def reset_db():
    """Reset database instance"""
    global _db_instance
    if _db_instance:
        _db_instance = None