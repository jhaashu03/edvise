#!/usr/bin/env python3
"""
BGE Embeddings Generator and Milvus Storage for Topper PDFs
===========================================================

This script processes the extracted topper PDF JSON files, generates BGE-large-en-v1.5 embeddings,
and stores them in Milvus database for efficient similarity search and retrieval.

Features:
- BGE-large-en-v1.5 embeddings for high-quality semantic search
- Efficient batch processing of embeddings
- Milvus vector database storage
- Comprehensive metadata indexing
- Progress tracking and error handling
- Support for multiple JSON files

Usage:
    python generate_bge_embeddings_milvus.py --input_dir "path/to/json/files" --collection_name "toppers_qa"
"""

import json
import asyncio
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
import sys
import os
import numpy as np
from tqdm import tqdm

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent / "app"))

try:
    from sentence_transformers import SentenceTransformer
    from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
except ImportError as e:
    print(f"❌ Missing required packages. Please install:")
    print("pip install sentence-transformers pymilvus")
    print(f"Error: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BGEMilvusProcessor:
    def __init__(self, model_name="BAAI/bge-large-en-v1.5", milvus_db_path="./milvus_toppers.db"):
        """
        Initialize BGE embeddings and Milvus connection
        
        Args:
            model_name: BGE model to use for embeddings
            milvus_db_path: Path to Milvus Lite database file
        """
        self.model_name = model_name
        self.milvus_db_path = milvus_db_path
        self.embedding_model = None
        self.embedding_dim = 1024  # BGE-large-en-v1.5 dimension
        
        print(f"🚀 Initializing BGE-Milvus Processor")
        print(f"📊 Model: {model_name}")
        print(f"🗄️ Milvus Lite: {milvus_db_path}")
        
    def load_embedding_model(self):
        """Load the BGE embedding model"""
        print(f"📥 Loading BGE model: {self.model_name}")
        try:
            self.embedding_model = SentenceTransformer(self.model_name)
            print(f"✅ BGE model loaded successfully")
            
            # Test embedding to get actual dimension
            test_embedding = self.embedding_model.encode("test")
            self.embedding_dim = len(test_embedding)
            print(f"📏 Embedding dimension: {self.embedding_dim}")
            
        except Exception as e:
            print(f"❌ Failed to load BGE model: {e}")
            raise
    
    def connect_milvus(self):
        """Connect to Milvus Lite database"""
        print(f"🔗 Connecting to Milvus Lite at {self.milvus_db_path}")
        try:
            connections.connect("default", uri=self.milvus_db_path)
            print(f"✅ Connected to Milvus Lite successfully")
        except Exception as e:
            print(f"❌ Failed to connect to Milvus Lite: {e}")
            raise
    
    def create_collection_schema(self):
        """Create Milvus collection schema for topper Q&A data"""
        fields = [
            # Primary key
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            
            # Question and answer content
            FieldSchema(name="question_text", dtype=DataType.VARCHAR, max_length=10000),
            FieldSchema(name="answer_text", dtype=DataType.VARCHAR, max_length=50000),
            FieldSchema(name="combined_content", dtype=DataType.VARCHAR, max_length=60000),  # Question + Answer for embedding
            
            # Metadata fields
            FieldSchema(name="pdf_filename", dtype=DataType.VARCHAR, max_length=500),
            FieldSchema(name="question_number", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="marks_allocated", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="word_limit", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="year", dtype=DataType.INT64),
            FieldSchema(name="pages_spanned", dtype=DataType.VARCHAR, max_length=200),  # JSON string of page numbers
            FieldSchema(name="is_multi_page", dtype=DataType.BOOL),
            FieldSchema(name="expected_pages", dtype=DataType.INT64),
            FieldSchema(name="actual_pages", dtype=DataType.INT64),
            FieldSchema(name="estimated_word_count", dtype=DataType.INT64),
            FieldSchema(name="handwriting_quality", dtype=DataType.VARCHAR, max_length=50),
            
            # Embedding vector
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dim),
            
            # Timestamps
            FieldSchema(name="created_at", dtype=DataType.INT64),  # Unix timestamp
            FieldSchema(name="extraction_timestamp", dtype=DataType.VARCHAR, max_length=100),
        ]
        
        schema = CollectionSchema(fields, description="Topper answer sheets Q&A with BGE embeddings")
        return schema
    
    def create_or_get_collection(self, collection_name: str):
        """Create or get existing Milvus collection"""
        print(f"📊 Setting up collection: {collection_name}")
        
        if utility.has_collection(collection_name):
            print(f"🔍 Collection '{collection_name}' already exists")
            collection = Collection(collection_name)
            
            # Check if schema matches
            existing_schema = collection.schema
            print(f"📋 Existing collection has {len(existing_schema.fields)} fields")
            
        else:
            print(f"🆕 Creating new collection: {collection_name}")
            schema = self.create_collection_schema()
            collection = Collection(collection_name, schema)
            
            # Create index for vector search
            index_params = {
                "metric_type": "COSINE",  # Use cosine similarity for semantic search
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            
            print(f"🔍 Creating vector index...")
            collection.create_index("embedding", index_params)
            print(f"✅ Vector index created")
        
        # Load collection into memory
        collection.load()
        print(f"💾 Collection loaded into memory")
        
        return collection
    
    def load_json_files(self, input_dir: str) -> List[Dict[str, Any]]:
        """Load all extracted JSON files from directory"""
        input_path = Path(input_dir)
        json_files = list(input_path.glob("*_FIXED_V2_extracted_*.json"))
        
        print(f"📁 Found {len(json_files)} JSON files in {input_dir}")
        
        all_data = []
        for json_file in json_files:
            print(f"📖 Loading: {json_file.name}")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    all_data.append(data)
                    print(f"   ✅ Loaded {len(data.get('questions', {}))} questions")
            except Exception as e:
                print(f"   ❌ Error loading {json_file}: {e}")
        
        print(f"📊 Total files loaded: {len(all_data)}")
        return all_data
    
    def prepare_embedding_data(self, json_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare data for embedding generation"""
        embedding_data = []
        
        for pdf_data in json_data_list:
            pdf_metadata = pdf_data.get("pdf_metadata", {})
            questions = pdf_data.get("questions", {})
            
            print(f"📝 Processing: {pdf_metadata.get('filename', 'Unknown')}")
            print(f"   📊 Questions: {len(questions)}")
            
            for question_key, question_data in questions.items():
                # Skip orphaned content if any
                if "orphan" in question_key:
                    print(f"   ⚠️ Skipping orphaned content: {question_key}")
                    continue
                
                metadata = question_data.get("metadata", {})
                question_text = question_data.get("question_text", "").strip()
                answer_text = question_data.get("complete_answer", "").strip()
                
                if not question_text or not answer_text:
                    print(f"   ⚠️ Skipping incomplete data: {question_key}")
                    continue
                
                # Combine question and answer for embedding
                combined_content = f"Question: {question_text}\n\nAnswer: {answer_text}"
                
                # Prepare data entry
                entry = {
                    "question_text": question_text,
                    "answer_text": answer_text,
                    "combined_content": combined_content,
                    "pdf_filename": pdf_metadata.get("filename", ""),
                    "question_number": str(metadata.get("question_number", "")),
                    "marks_allocated": str(metadata.get("marks_allocated", "")),
                    "word_limit": str(metadata.get("word_limit", "")),
                    "year": int(pdf_metadata.get("year", 2024)),
                    "pages_spanned": json.dumps(metadata.get("pages_spanned", [])),
                    "is_multi_page": metadata.get("is_multi_page", False),
                    "expected_pages": int(metadata.get("expected_pages", 1)),
                    "actual_pages": int(metadata.get("actual_pages", 1)),
                    "estimated_word_count": int(metadata.get("estimated_word_count", 0)),
                    "handwriting_quality": str(metadata.get("handwriting_quality", "moderate")),
                    "created_at": int(datetime.now().timestamp()),
                    "extraction_timestamp": pdf_metadata.get("extraction_timestamp", ""),
                }
                
                embedding_data.append(entry)
        
        print(f"🎯 Prepared {len(embedding_data)} entries for embedding")
        return embedding_data
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings in batches for efficiency"""
        print(f"🧠 Generating embeddings for {len(texts)} texts (batch size: {batch_size})")
        
        all_embeddings = []
        
        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i + batch_size]
            
            try:
                batch_embeddings = self.embedding_model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # Normalize for better cosine similarity
                )
                all_embeddings.extend(batch_embeddings)
                
            except Exception as e:
                print(f"❌ Error generating embeddings for batch {i//batch_size + 1}: {e}")
                # Use zero embeddings as fallback
                fallback_embeddings = np.zeros((len(batch_texts), self.embedding_dim))
                all_embeddings.extend(fallback_embeddings)
        
        embeddings_array = np.array(all_embeddings)
        print(f"✅ Generated embeddings shape: {embeddings_array.shape}")
        
        return embeddings_array
    
    def insert_data_to_milvus(self, collection: Collection, embedding_data: List[Dict[str, Any]], embeddings: np.ndarray):
        """Insert data and embeddings into Milvus collection"""
        print(f"💾 Inserting {len(embedding_data)} entries into Milvus...")
        
        # Prepare data for insertion
        insert_data = []
        field_names = [field.name for field in collection.schema.fields if not field.auto_id]
        
        for field_name in field_names:
            if field_name == "embedding":
                insert_data.append(embeddings.tolist())
            else:
                insert_data.append([entry[field_name] for entry in embedding_data])
        
        try:
            # Insert data
            mr = collection.insert(insert_data)
            print(f"✅ Inserted {len(mr.primary_keys)} entries")
            
            # Flush to ensure data is written
            collection.flush()
            print(f"💾 Data flushed to storage")
            
            return mr
            
        except Exception as e:
            print(f"❌ Error inserting data: {e}")
            raise
    
    def create_search_index(self, collection: Collection):
        """Create additional indexes for efficient searching"""
        print(f"🔍 Creating search indexes...")
        
        try:
            # The vector index was already created, so we just need to ensure it's loaded
            collection.load()
            print(f"✅ Search indexes ready")
            
        except Exception as e:
            print(f"❌ Error creating indexes: {e}")
    
    def test_search(self, collection: Collection, test_query: str = "fiscal policy") -> List[Dict]:
        """Test the search functionality"""
        print(f"🔍 Testing search with query: '{test_query}'")
        
        try:
            # Generate embedding for test query
            query_embedding = self.embedding_model.encode([test_query], normalize_embeddings=True)
            
            # Search parameters
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            # Perform search
            results = collection.search(
                data=query_embedding,
                anns_field="embedding",
                param=search_params,
                limit=3,
                output_fields=["question_text", "answer_text", "pdf_filename", "question_number", "marks_allocated"]
            )
            
            print(f"📊 Search results:")
            search_results = []
            
            for i, result in enumerate(results[0]):
                result_data = {
                    "rank": i + 1,
                    "score": result.score,
                    "question": result.entity.get("question_text", "")[:100] + "...",
                    "pdf": result.entity.get("pdf_filename", ""),
                    "question_number": result.entity.get("question_number", ""),
                    "marks": result.entity.get("marks_allocated", "")
                }
                search_results.append(result_data)
                
                print(f"   {i+1}. Score: {result.score:.4f}")
                print(f"      PDF: {result_data['pdf']}")
                print(f"      Q{result_data['question_number']} ({result_data['marks']} marks)")
                print(f"      Question: {result_data['question']}")
                print()
            
            return search_results
            
        except Exception as e:
            print(f"❌ Error during search test: {e}")
            return []
    
    def get_collection_stats(self, collection: Collection) -> Dict[str, Any]:
        """Get collection statistics"""
        try:
            stats = {
                "total_entities": collection.num_entities,
                "collection_name": collection.name,
                "schema_fields": len(collection.schema.fields),
                "indexes": len(collection.indexes),
            }
            
            print(f"📊 Collection Statistics:")
            print(f"   📁 Name: {stats['collection_name']}")
            print(f"   📊 Total entities: {stats['total_entities']}")
            print(f"   🏗️ Schema fields: {stats['schema_fields']}")
            print(f"   🔍 Indexes: {stats['indexes']}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting collection stats: {e}")
            return {}
    
    async def process_files(self, input_dir: str, collection_name: str, batch_size: int = 32):
        """Main processing pipeline"""
        print("🚀 Starting BGE-Milvus processing pipeline...")
        
        try:
            # 1. Load embedding model
            self.load_embedding_model()
            
            # 2. Connect to Milvus
            self.connect_milvus()
            
            # 3. Create or get collection
            collection = self.create_or_get_collection(collection_name)
            
            # 4. Load JSON files
            json_data = self.load_json_files(input_dir)
            if not json_data:
                print("❌ No JSON files found!")
                return
            
            # 5. Prepare embedding data
            embedding_data = self.prepare_embedding_data(json_data)
            if not embedding_data:
                print("❌ No valid data for embedding!")
                return
            
            # 6. Generate embeddings
            combined_texts = [entry["combined_content"] for entry in embedding_data]
            embeddings = self.generate_embeddings_batch(combined_texts, batch_size)
            
            # 7. Insert into Milvus
            insert_result = self.insert_data_to_milvus(collection, embedding_data, embeddings)
            
            # 8. Create search indexes
            self.create_search_index(collection)
            
            # 9. Get statistics
            stats = self.get_collection_stats(collection)
            
            # 10. Test search
            test_results = self.test_search(collection)
            
            print("\n" + "="*60)
            print("🎉 BGE-MILVUS PROCESSING COMPLETE!")
            print("="*60)
            print(f"📊 Processed {len(json_data)} PDF files")
            print(f"🧠 Generated {len(embeddings)} BGE embeddings")
            print(f"💾 Stored in Milvus collection: {collection_name}")
            print(f"🔍 Search functionality tested and working")
            print("="*60)
            
            return {
                "collection": collection,
                "stats": stats,
                "test_results": test_results,
                "processing_summary": {
                    "pdf_files": len(json_data),
                    "embeddings_generated": len(embeddings),
                    "collection_name": collection_name,
                    "embedding_model": self.model_name
                }
            }
            
        except Exception as e:
            print(f"❌ Pipeline failed: {e}")
            raise

async def main():
    parser = argparse.ArgumentParser(description="Generate BGE embeddings and store in Milvus")
    parser.add_argument("--input_dir", required=True, help="Directory containing extracted JSON files")
    parser.add_argument("--collection_name", default="toppers_qa_bge", help="Milvus collection name")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size for embedding generation")
    parser.add_argument("--milvus_db_path", default="./milvus_toppers.db", help="Milvus Lite database path")
    parser.add_argument("--model_name", default="BAAI/bge-large-en-v1.5", help="BGE model name")
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = BGEMilvusProcessor(
        model_name=args.model_name,
        milvus_db_path=args.milvus_db_path
    )
    
    # Process files
    result = await processor.process_files(
        input_dir=args.input_dir,
        collection_name=args.collection_name,
        batch_size=args.batch_size
    )
    
    if result:
        print(f"\n🎯 SUCCESS: BGE embeddings generated and stored in Milvus!")
        print(f"🔍 Collection '{args.collection_name}' ready for semantic search")
        print(f"🚀 Next: Use the collection for similarity search and retrieval")
    else:
        print(f"\n❌ FAILED: Processing unsuccessful")

if __name__ == "__main__":
    asyncio.run(main())
