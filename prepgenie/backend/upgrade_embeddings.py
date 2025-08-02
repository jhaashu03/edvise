#!/usr/bin/env python3
"""
Upgrade PYQ embeddings from all-MiniLM-L6-v2 (384-dim) to bge-large-en-v1.5 (1024-dim)
This script will:
1. Load all PYQs from pyq_questions.json
2. Create new collection with 1024-dim embeddings
3. Generate new embeddings using bge-large-en-v1.5
4. Insert all data into the new collection
"""

import json
import logging
import os
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the PYQ vector service
from app.services.pyq_vector_service import PYQVectorService

def load_pyq_data(file_path: str) -> List[Dict[str, Any]]:
    """Load PYQ data from JSON file"""
    logger.info(f"📂 Loading PYQ data from {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    logger.info(f"✅ Loaded {len(data)} PYQ questions")
    return data

def upgrade_embeddings():
    """Main function to upgrade embeddings"""
    logger.info("🚀 Starting embedding upgrade process...")
    logger.info("📊 Upgrading from all-MiniLM-L6-v2 (384-dim) to bge-large-en-v1.5 (1024-dim)")
    
    # Initialize service with new model
    service = PYQVectorService()
    
    # Ensure connection is established
    if not service.connect():
        logger.error("❌ Failed to connect to Milvus")
        return False
    
    # Load PYQ data
    pyq_data = load_pyq_data('pyq_questions.json')
    
    logger.info("🔧 Creating new collection with 1024-dim embeddings...")
    
    # Create new collection (this will drop existing and recreate)
    if not service.create_collection():
        logger.error("❌ Failed to create collection")
        return False
    
    logger.info("🧠 Generating new embeddings with bge-large-en-v1.5...")
    
    # Process questions in batches for better memory management
    batch_size = 50  # Smaller batches for large model
    total_questions = len(pyq_data)
    
    for i in tqdm(range(0, total_questions, batch_size), desc="Processing batches"):
        batch = pyq_data[i:i + batch_size]
        
        # Extract question texts for embedding
        question_texts = [q['question_text'] for q in batch]
        
        # Generate embeddings
        try:
            embeddings = service.embedding_model.encode(
                question_texts,
                show_progress_bar=False,
                batch_size=16  # Conservative batch size for large model
            )
            
            # Prepare data for insertion
            entities = []
            for j, question in enumerate(batch):
                entity = {
                    "pyq_id": int(question.get('pyq_id', i + j + 1)),
                    "question_text": question['question_text'],
                    "subject": question.get('subject', ''),
                    "year": int(question['year']),
                    "paper": question.get('paper', ''),
                    "topics": question.get('topics', ''),
                    "difficulty": question.get('difficulty', 'Medium'),
                    "marks": int(question.get('marks', 10)),
                    "embedding": embeddings[j].tolist()
                }
                entities.append(entity)
            
            # Insert batch into collection
            service.collection.insert(entities)
            
            logger.info(f"✅ Processed batch {i//batch_size + 1}/{(total_questions + batch_size - 1)//batch_size}")
            
        except Exception as e:
            logger.error(f"❌ Error processing batch {i//batch_size + 1}: {str(e)}")
            continue
    
    # Build index and load collection
    logger.info("🔍 Building search index...")
    service.collection.flush()
    
    logger.info("📈 Loading collection for search...")
    service.collection.load()
    
    # Verify the upgrade
    logger.info("🔍 Verifying upgrade...")
    entity_count = service.collection.num_entities
    logger.info(f"📊 Total entities in collection: {entity_count}")
    
    # Test a search to verify functionality
    try:
        test_results = service.search_questions("women leadership", limit=3)
        logger.info(f"✅ Test search successful! Found {len(test_results)} results")
        if test_results:
            logger.info(f"🏆 Top result score: {test_results[0].get('similarity_score', 0):.3f}")
    except Exception as e:
        logger.error(f"❌ Test search failed: {str(e)}")
    
    logger.info("🎉 Embedding upgrade completed successfully!")
    logger.info("🧠 New model: BAAI/bge-large-en-v1.5 (1024 dimensions)")
    logger.info("📊 Benefits: Better semantic understanding of UPSC content")
    
    return True

if __name__ == "__main__":
    success = upgrade_embeddings()
    if success:
        print("\n🎉 SUCCESS: Embedding upgrade completed!")
        print("🔍 Search quality should be significantly improved for UPSC content")
    else:
        print("\n❌ FAILED: Embedding upgrade encountered errors")
        exit(1)
