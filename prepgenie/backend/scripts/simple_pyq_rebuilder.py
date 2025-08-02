#!/usr/bin/env python3
"""
Simple PYQ Database Rebuilder - Uses cached models to avoid SSL issues
"""

import os
import sys
import re
import logging
from pathlib import Path
from typing import List, Dict, Any
from docx import Document
from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
import numpy as np

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.append(str(backend_dir))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplePYQRebuilder:
    def __init__(self):
        self.pyq_dir = "/Users/a0j0agc/Desktop/Personal/Dump/PYQ/MAINS"
        self.embedding_model = None
        self.collection = None
        
    def initialize_embedding_model(self):
        """Initialize embedding model using cached version"""
        try:
            logger.info("🧠 Loading cached embedding model...")
            
            # Import here to avoid SSL issues during startup
            from sentence_transformers import SentenceTransformer
            
            # Use the model that's already cached from your working system
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            logger.info("💡 The model should already be cached from your working system")
            raise
    
    def connect_to_milvus(self):
        """Connect to Milvus and create collection"""
        try:
            logger.info("🔌 Connecting to Milvus...")
            connections.connect(alias="default", uri="./milvus_lite_local.db")
            
            # Define collection schema matching your existing structure
            fields = [
                FieldSchema(name="pyq_id", dtype=DataType.VARCHAR, max_length=100, is_primary=True),
                FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=5000),
                FieldSchema(name="year", dtype=DataType.INT64),
                FieldSchema(name="paper", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="question_number", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="marks", dtype=DataType.INT64),
                FieldSchema(name="word_limit", dtype=DataType.INT64),
                FieldSchema(name="subject", dtype=DataType.VARCHAR, max_length=100),
                FieldSchema(name="topics", dtype=DataType.VARCHAR, max_length=1000),
                FieldSchema(name="difficulty", dtype=DataType.VARCHAR, max_length=20),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384)
            ]
            
            schema = CollectionSchema(fields, "PYQ Questions Collection")
            
            # Drop existing collection if exists
            if utility.has_collection("pyq_embeddings"):
                utility.drop_collection("pyq_embeddings")
                logger.info("🗑️ Dropped existing collection")
            
            # Create new collection
            self.collection = Collection("pyq_embeddings", schema)
            logger.info("✅ Created new Milvus collection")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to Milvus: {e}")
            raise
    
    def parse_sample_questions(self) -> List[Dict[str, Any]]:
        """Create sample questions to test the system"""
        logger.info("📝 Creating sample questions for testing...")
        
        sample_questions = [
            {
                'pyq_id': '2024_GS1_Q1',
                'question_text': 'Discuss the role of women in the freedom struggle especially during the Gandhian phase.',
                'year': 2024,
                'paper': 'GS1',
                'question_number': 'Q.1',
                'marks': 10,
                'word_limit': 150,
                'subject': 'History, Geography, Society',
                'topics': 'women, freedom struggle, gandhi',
                'difficulty': 'Medium'
            },
            {
                'pyq_id': '2024_GS2_Q1',
                'question_text': 'Empowering women is the key to control population growth. Discuss.',
                'year': 2024,
                'paper': 'GS2',
                'question_number': 'Q.1',
                'marks': 10,
                'word_limit': 150,
                'subject': 'Governance, Constitution, Social Justice',
                'topics': 'women, empowerment, population',
                'difficulty': 'Medium'
            },
            {
                'pyq_id': '2024_GS3_Q1',
                'question_text': 'What are the challenges to our cultural practices in the name of secularism?',
                'year': 2024,
                'paper': 'GS3',
                'question_number': 'Q.1',
                'marks': 10,
                'word_limit': 150,
                'subject': 'Technology, Economy, Environment',
                'topics': 'culture, secularism, practices',
                'difficulty': 'Medium'
            },
            {
                'pyq_id': '2023_GS1_Q1',
                'question_text': 'Highlight the differences in the approach of Subhash Chandra Bose and Mahatma Gandhi in the struggle for freedom.',
                'year': 2023,
                'paper': 'GS1',
                'question_number': 'Q.1',
                'marks': 12,
                'word_limit': 200,
                'subject': 'History, Geography, Society',
                'topics': 'freedom struggle, gandhi, bose',
                'difficulty': 'Medium'
            },
            {
                'pyq_id': '2023_GS2_Q1',
                'question_text': 'Many voices had strengthened and enriched the nationalist movement during the Gandhian phase. Elaborate.',
                'year': 2023,
                'paper': 'GS2',
                'question_number': 'Q.1',
                'marks': 15,
                'word_limit': 250,
                'subject': 'Governance, Constitution, Social Justice',
                'topics': 'nationalism, gandhi, movement',
                'difficulty': 'Hard'
            }
        ]
        
        logger.info(f"📊 Created {len(sample_questions)} sample questions")
        return sample_questions
    
    def generate_embeddings(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for questions"""
        logger.info(f"🧠 Generating embeddings for {len(questions)} questions...")
        
        question_texts = [q['question_text'] for q in questions]
        embeddings = self.embedding_model.encode(question_texts, show_progress_bar=True)
        
        # Add embeddings to question data
        for i, question in enumerate(questions):
            question['embedding'] = embeddings[i].tolist()
        
        logger.info("✅ Embeddings generated successfully")
        return questions
    
    def insert_to_milvus(self, questions: List[Dict[str, Any]]):
        """Insert questions into Milvus collection"""
        logger.info(f"💾 Inserting {len(questions)} questions into Milvus...")
        
        # Prepare data for insertion
        data = [
            [q['pyq_id'] for q in questions],
            [q['question_text'] for q in questions],
            [q['year'] for q in questions],
            [q['paper'] for q in questions],
            [q['question_number'] for q in questions],
            [q['marks'] for q in questions],
            [q['word_limit'] for q in questions],
            [q['subject'] for q in questions],
            [q['topics'] for q in questions],
            [q['difficulty'] for q in questions],
            [q['embedding'] for q in questions]
        ]
        
        # Insert data
        self.collection.insert(data)
        self.collection.flush()
        
        logger.info("✅ Data inserted successfully")
    
    def create_index(self):
        """Create index for efficient search"""
        logger.info("🔍 Creating search index...")
        
        index_params = {
            "metric_type": "COSINE",
            "index_type": "FLAT",
            "params": {}
        }
        
        self.collection.create_index("embedding", index_params)
        self.collection.load()
        
        logger.info("✅ Index created and collection loaded")
    
    def rebuild_database(self):
        """Main function to rebuild the database with sample data"""
        try:
            logger.info("🚀 Starting simple PYQ database rebuild...")
            
            # Initialize components
            self.initialize_embedding_model()
            self.connect_to_milvus()
            
            # Create sample questions (you can expand this later)
            questions = self.parse_sample_questions()
            
            # Generate embeddings
            questions = self.generate_embeddings(questions)
            
            # Insert into Milvus
            self.insert_to_milvus(questions)
            
            # Create index
            self.create_index()
            
            # Final stats
            entity_count = self.collection.num_entities
            logger.info(f"🎉 Database rebuild complete! Total entities: {entity_count}")
            
            # Test search
            self.test_search()
            
        except Exception as e:
            logger.error(f"❌ Database rebuild failed: {e}")
            raise
        finally:
            connections.disconnect("default")
    
    def test_search(self):
        """Test the rebuilt database"""
        logger.info("🧪 Testing search functionality...")
        
        try:
            # Test search
            search_params = {"metric_type": "COSINE", "params": {}}
            
            # Create a test query embedding
            test_query = "women leadership empowerment"
            query_embedding = self.embedding_model.encode([test_query])
            
            # Search
            results = self.collection.search(
                data=query_embedding.tolist(),
                anns_field="embedding",
                param=search_params,
                limit=3,
                output_fields=["pyq_id", "question_text", "year", "paper"]
            )
            
            logger.info("🔍 Search test results:")
            for i, hit in enumerate(results[0]):
                logger.info(f"  {i+1}. {hit.entity.get('pyq_id')} (score: {hit.score:.3f})")
                logger.info(f"     {hit.entity.get('question_text')[:80]}...")
            
        except Exception as e:
            logger.error(f"❌ Search test failed: {e}")

if __name__ == "__main__":
    rebuilder = SimplePYQRebuilder()
    rebuilder.rebuild_database()
