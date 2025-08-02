#!/usr/bin/env python3
"""
Quick PYQ Database Rebuilder
Creates a fresh database with sample questions using shared connection approach
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickPYQRebuilder:
    def __init__(self):
        self.collection_name = "pyq_embeddings"
        self.db_path = "./milvus_lite_local.db"
        
    def connect(self):
        """Connect to Milvus database"""
        try:
            # Make sure we start fresh
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"🗑️ Removed existing database: {self.db_path}")
            
            # Connect to fresh database
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            logger.info("✅ Connected to fresh Milvus database")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False
    
    def create_collection(self):
        """Create collection with proper schema"""
        try:
            # Define collection schema
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="pyq_id", dtype=DataType.INT64),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            
            schema = CollectionSchema(fields, "PYQ embeddings for semantic search")
            
            # Create collection
            collection = Collection(self.collection_name, schema)
            logger.info("✅ Created collection with schema")
            return collection
        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
            return None
    
    def create_sample_data(self):
        """Create sample data for testing"""
        # Create random embeddings (384-dim)
        sample_data = [
            {
                "pyq_id": 1001,
                "question_text": "Discuss the role of women in the freedom struggle especially during the Gandhian phase.",
                "subject": "Modern History",
                "year": 2023,
                "paper": "GS1",
                "topics": "women, freedom struggle, gandhi",
                "difficulty": "Medium",
                "marks": 10,
                "embedding": list(np.random.rand(384).astype(float))
            },
            {
                "pyq_id": 1002,
                "question_text": "Empowering women is the key to control population growth. Discuss.",
                "subject": "Indian Society",
                "year": 2023,
                "paper": "GS2",
                "topics": "women, population, empowerment",
                "difficulty": "Medium",
                "marks": 10,
                "embedding": list(np.random.rand(384).astype(float))
            },
            {
                "pyq_id": 1003,
                "question_text": "What are the challenges to our cultural practices in the name of secularism?",
                "subject": "Indian Society",
                "year": 2023,
                "paper": "GS2",
                "topics": "culture, secularism",
                "difficulty": "Medium",
                "marks": 10,
                "embedding": list(np.random.rand(384).astype(float))
            },
            {
                "pyq_id": 1004,
                "question_text": "Many voices had strengthened and enriched the nationalist movement during the Gandhian phase. Elaborate.",
                "subject": "Modern History",
                "year": 2023,
                "paper": "GS1",
                "topics": "nationalism, freedom struggle, gandhi",
                "difficulty": "Hard",
                "marks": 15,
                "embedding": list(np.random.rand(384).astype(float))
            },
            {
                "pyq_id": 1005,
                "question_text": "Assess the role of British imperial power in complicating the process of transfer of power during the 1940s.",
                "subject": "Modern History",
                "year": 2022,
                "paper": "GS1",
                "topics": "british, independence, transfer of power",
                "difficulty": "Hard", 
                "marks": 15,
                "embedding": list(np.random.rand(384).astype(float))
            }
        ]
        
        logger.info(f"📝 Created {len(sample_data)} sample questions")
        return sample_data
    
    def insert_data(self, collection, data):
        """Insert data into collection"""
        try:
            # Prepare data for insertion
            pyq_ids = [item["pyq_id"] for item in data]
            questions = [item["question_text"] for item in data]
            subjects = [item["subject"] for item in data]
            years = [item["year"] for item in data]
            papers = [item["paper"] for item in data]
            topics = [item["topics"] for item in data]
            difficulties = [item["difficulty"] for item in data]
            marks = [item["marks"] for item in data]
            embeddings = [item["embedding"] for item in data]
            
            # Insert data
            collection.insert([
                pyq_ids, questions, subjects, years, papers, 
                topics, difficulties, marks, embeddings
            ])
            collection.flush()
            logger.info(f"✅ Inserted {len(data)} questions")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert data: {e}")
            return False
    
    def create_index(self, collection):
        """Create index for search"""
        try:
            # Create index
            index_params = {
                "metric_type": "COSINE",
                "index_type": "FLAT",
                "params": {}
            }
            collection.create_index("embedding", index_params)
            collection.load()
            logger.info("✅ Created search index")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
            return False
    
    def rebuild(self):
        """Rebuild database with sample data"""
        try:
            logger.info("🚀 Starting database rebuild...")
            
            # Connect to database
            if not self.connect():
                return False
            
            # Create collection
            collection = self.create_collection()
            if not collection:
                return False
            
            # Create sample data
            data = self.create_sample_data()
            
            # Insert data
            if not self.insert_data(collection, data):
                return False
            
            # Create index
            if not self.create_index(collection):
                return False
            
            # Verify collection
            count = collection.num_entities
            logger.info(f"✅ Database rebuild complete! {count} entities in collection.")
            return True
        except Exception as e:
            logger.error(f"❌ Database rebuild failed: {e}")
            return False
        finally:
            connections.disconnect("default")

if __name__ == "__main__":
    rebuilder = QuickPYQRebuilder()
    success = rebuilder.rebuild()
    if success:
        print("\n✅ PYQ database successfully rebuilt with sample questions!")
        print("🚀 Now restart your server to use the new database.")
    else:
        print("\n❌ Failed to rebuild PYQ database.")
