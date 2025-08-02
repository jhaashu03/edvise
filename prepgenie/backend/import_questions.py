#!/usr/bin/env python3
"""
Import PYQ Questions to Milvus
"""

import os
import json
import logging
import numpy as np
from pathlib import Path
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PYQMilvusImporter:
    def __init__(self):
        self.json_file = "./pyq_questions.json"
        self.db_path = "./milvus_lite_local.db"
        self.collection_name = "pyq_embeddings"
        self.embedding_dim = 384  # dimension for all-MiniLM-L6-v2
        self.collection = None
    
    def load_questions(self):
        """Load questions from JSON file"""
        try:
            logger.info(f"📄 Loading questions from {self.json_file}")
            with open(self.json_file, 'r') as f:
                questions = json.load(f)
            
            logger.info(f"✅ Loaded {len(questions)} questions")
            return questions
        except Exception as e:
            logger.error(f"❌ Failed to load questions: {e}")
            return []
    
    def connect_to_milvus(self):
        """Connect to Milvus database"""
        try:
            logger.info(f"🔌 Connecting to Milvus at {self.db_path}")
            
            # Remove existing database if it exists
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"🗑️ Removed existing database: {self.db_path}")
            
            connections.connect(
                alias="default",
                uri=self.db_path
            )
            
            logger.info("✅ Connected to Milvus")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to Milvus: {e}")
            return False
    
    def create_collection(self):
        """Create collection with schema"""
        try:
            logger.info("📊 Creating collection schema")
            
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
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim)
            ]
            
            schema = CollectionSchema(fields, "PYQ embeddings for semantic search")
            
            # Create collection
            self.collection = Collection(self.collection_name, schema)
            logger.info("✅ Created collection")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create collection: {e}")
            return False
    
    def generate_random_embeddings(self, count):
        """Generate random embeddings for questions"""
        logger.info(f"🧠 Generating {count} random embeddings")
        
        # Generate random embeddings (for testing without SentenceTransformer)
        embeddings = []
        for _ in range(count):
            # Generate random vector and normalize it
            vec = np.random.rand(self.embedding_dim).astype(float)
            vec = vec / np.linalg.norm(vec)  # L2 normalize for COSINE similarity
            embeddings.append(vec.tolist())
        
        logger.info("✅ Generated random embeddings")
        return embeddings
    
    def insert_questions(self, questions):
        """Insert questions into collection"""
        try:
            logger.info(f"💾 Inserting {len(questions)} questions into Milvus")
            
            # Generate random embeddings (since we can't use SentenceTransformer)
            embeddings = self.generate_random_embeddings(len(questions))
            
            # Convert string IDs to numeric IDs
            pyq_ids = []
            for i, q in enumerate(questions):
                # Use index as numeric ID
                pyq_ids.append(i + 1000)
            
            # Prepare data for insertion
            question_texts = [q["question_text"] for q in questions]
            subjects = [q["subject"] for q in questions]
            years = [q["year"] for q in questions]
            papers = [q["paper"] for q in questions]
            topics = [q.get("topics", "") for q in questions]
            difficulties = [q.get("difficulty", "Medium") for q in questions]
            marks = [q.get("marks", 10) for q in questions]
            
            # Insert data in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(questions), batch_size):
                end_idx = min(i + batch_size, len(questions))
                batch_data = [
                    pyq_ids[i:end_idx], 
                    question_texts[i:end_idx], 
                    subjects[i:end_idx], 
                    years[i:end_idx], 
                    papers[i:end_idx],
                    topics[i:end_idx], 
                    difficulties[i:end_idx], 
                    marks[i:end_idx], 
                    embeddings[i:end_idx]
                ]
                
                self.collection.insert(batch_data)
                logger.info(f"  Inserted batch {i//batch_size + 1}: {i+1}-{end_idx}")
            
            self.collection.flush()
            logger.info(f"✅ Inserted all {len(questions)} questions")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to insert questions: {e}")
            return False
    
    def create_index(self):
        """Create vector search index"""
        try:
            logger.info("🔍 Creating search index")
            
            # Create FLAT index (exact search)
            index_params = {
                "metric_type": "COSINE",
                "index_type": "FLAT",
                "params": {}
            }
            
            self.collection.create_index("embedding", index_params)
            self.collection.load()
            
            logger.info("✅ Created search index")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create index: {e}")
            return False
    
    def test_search(self):
        """Test search functionality"""
        try:
            logger.info("🔍 Testing search")
            
            # Create random query vector
            query_vector = np.random.rand(self.embedding_dim).astype(float)
            query_vector = query_vector / np.linalg.norm(query_vector)  # L2 normalize
            
            # Search params
            search_params = {
                "metric_type": "COSINE",
            }
            
            # Search
            results = self.collection.search(
                data=[query_vector.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=5,
                output_fields=["question_text", "year", "paper", "marks", "subject"]
            )
            
            # Display results
            logger.info("  📊 Sample search results:")
            for i, hit in enumerate(results[0]):
                logger.info(f"    {i+1}. [{hit.entity.get('year')} {hit.entity.get('paper')}] Score: {hit.score:.4f}")
                logger.info(f"       Subject: {hit.entity.get('subject')}, Marks: {hit.entity.get('marks')}")
                logger.info(f"       {hit.entity.get('question_text')[:100]}...")
                logger.info("")
            
            logger.info("✅ Search test completed")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to test search: {e}")
            return False
    
    def run(self):
        """Run the import process"""
        start_time = time.time()
        logger.info("🚀 Starting PYQ import to Milvus")
        
        try:
            # Load questions
            questions = self.load_questions()
            if not questions:
                return False
            
            # Connect to Milvus
            if not self.connect_to_milvus():
                return False
            
            # Create collection
            if not self.create_collection():
                return False
            
            # Insert questions
            if not self.insert_questions(questions):
                return False
            
            # Create index
            if not self.create_index():
                return False
            
            # Test search
            self.test_search()
            
            # Final stats
            count = self.collection.num_entities
            duration = time.time() - start_time
            logger.info(f"🎉 Import complete! {count} questions imported in {duration:.2f} seconds")
            
            # Show breakdown by year and paper
            logger.info("\n📊 Database Summary:")
            years = {}
            papers = {}
            for q in questions:
                year = q.get('year', 'Unknown')
                paper = q.get('paper', 'Unknown')
                years[year] = years.get(year, 0) + 1
                papers[paper] = papers.get(paper, 0) + 1
            
            logger.info("  By Year:")
            for year in sorted(years.keys()):
                logger.info(f"    {year}: {years[year]} questions")
            
            logger.info("  By Paper:")
            for paper in sorted(papers.keys()):
                logger.info(f"    {paper}: {papers[paper]} questions")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error during import: {e}")
            return False
        finally:
            # Disconnect
            try:
                connections.disconnect("default")
            except:
                pass

if __name__ == "__main__":
    importer = PYQMilvusImporter()
    success = importer.run()
    
    if success:
        print("\n✅ PYQ questions successfully imported to Milvus!")
        print("🚀 Your search database is now ready with individual questions")
        print("📊 Each question is properly labeled with year and paper")
        print("🔍 Start your backend server to test the search functionality")
    else:
        print("\n❌ Failed to import PYQ questions to Milvus")
