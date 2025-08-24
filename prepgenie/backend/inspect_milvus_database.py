#!/usr/bin/env python3
"""
Milvus Database Inspector for Topper Q&A Data
============================================

This script inspects the Milvus database to show how the BGE embeddings 
and metadata are stored, and provides search functionality.

Usage:
    python inspect_milvus_database.py --collection_name "toppers_qa_aayushi_bge"
"""

import json
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd

try:
    from pymilvus import connections, Collection, utility
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    print(f"❌ Missing required packages. Please install:")
    print("pip install pymilvus sentence-transformers pandas")
    print(f"Error: {e}")
    sys.exit(1)

class MilvusInspector:
    def __init__(self, milvus_db_path="./milvus_toppers.db"):
        """Initialize Milvus inspector"""
        self.milvus_db_path = milvus_db_path
        self.embedding_model = None
        
        print(f"🔍 Milvus Database Inspector")
        print(f"🗄️ Database: {milvus_db_path}")
    
    def connect_milvus(self):
        """Connect to Milvus Lite database"""
        print(f"🔗 Connecting to Milvus Lite...")
        try:
            connections.connect("default", uri=self.milvus_db_path)
            print(f"✅ Connected successfully")
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            raise
    
    def list_collections(self):
        """List all collections in the database"""
        print(f"\n📊 Collections in database:")
        try:
            collections = utility.list_collections()
            if collections:
                for i, collection_name in enumerate(collections, 1):
                    print(f"   {i}. {collection_name}")
                return collections
            else:
                print("   ⚠️ No collections found")
                return []
        except Exception as e:
            print(f"❌ Error listing collections: {e}")
            return []
    
    def inspect_collection(self, collection_name: str):
        """Inspect a specific collection"""
        print(f"\n🔍 Inspecting collection: {collection_name}")
        
        try:
            if not utility.has_collection(collection_name):
                print(f"❌ Collection '{collection_name}' does not exist")
                return None
            
            collection = Collection(collection_name)
            collection.load()
            
            # Get basic statistics
            print(f"\n📈 Collection Statistics:")
            print(f"   📁 Name: {collection.name}")
            print(f"   📊 Total entities: {collection.num_entities}")
            print(f"   🏗️ Schema fields: {len(collection.schema.fields)}")
            print(f"   🔍 Indexes: {len(collection.indexes)}")
            
            # Show schema
            print(f"\n🏗️ Schema Fields:")
            for i, field in enumerate(collection.schema.fields, 1):
                field_info = f"   {i}. {field.name} ({field.dtype})"
                if hasattr(field, 'max_length') and field.max_length:
                    field_info += f" [max_length: {field.max_length}]"
                if hasattr(field, 'dim') and field.dim:
                    field_info += f" [dim: {field.dim}]"
                if field.is_primary:
                    field_info += " [PRIMARY KEY]"
                if field.auto_id:
                    field_info += " [AUTO_ID]"
                print(field_info)
            
            # Show indexes
            print(f"\n🔍 Indexes:")
            for i, index in enumerate(collection.indexes, 1):
                print(f"   {i}. Field: {index.field_name}")
                print(f"      Type: {index.params.get('index_type', 'Unknown')}")
                print(f"      Metric: {index.params.get('metric_type', 'Unknown')}")
            
            return collection
            
        except Exception as e:
            print(f"❌ Error inspecting collection: {e}")
            return None
    
    def sample_data(self, collection: Collection, limit: int = 5):
        """Sample some data from the collection"""
        print(f"\n📋 Sample Data (first {limit} entries):")
        
        try:
            # Get field names (excluding vector field for readability)
            field_names = [field.name for field in collection.schema.fields 
                          if field.dtype.name != 'FLOAT_VECTOR' and not field.auto_id]
            
            # Query sample data
            results = collection.query(
                expr="",  # Empty expression means get all
                output_fields=field_names,
                limit=limit
            )
            
            if not results:
                print("   ⚠️ No data found")
                return
            
            # Display in a structured format
            for i, result in enumerate(results, 1):
                print(f"\n   📄 Entry {i}:")
                print(f"      🆔 ID: {result.get('id', 'N/A')}")
                print(f"      📝 Question: {result.get('question_text', 'N/A')[:100]}...")
                print(f"      📊 Q Number: {result.get('question_number', 'N/A')}")
                print(f"      🎯 Marks: {result.get('marks_allocated', 'N/A')}")
                print(f"      📄 PDF: {result.get('pdf_filename', 'N/A')}")
                print(f"      📅 Year: {result.get('year', 'N/A')}")
                print(f"      📏 Pages: {result.get('pages_spanned', 'N/A')}")
                print(f"      📊 Word Count: {result.get('estimated_word_count', 'N/A')}")
                print(f"      🏆 Quality: {result.get('handwriting_quality', 'N/A')}")
                
                # Show answer preview
                answer_text = result.get('answer_text', 'N/A')
                if len(answer_text) > 200:
                    answer_preview = answer_text[:200] + "..."
                else:
                    answer_preview = answer_text
                print(f"      📝 Answer: {answer_preview}")
                
        except Exception as e:
            print(f"❌ Error sampling data: {e}")
    
    def show_data_distribution(self, collection: Collection):
        """Show data distribution statistics"""
        print(f"\n📊 Data Distribution:")
        
        try:
            # Get all data for analysis
            results = collection.query(
                expr="",
                output_fields=["question_number", "marks_allocated", "year", "pdf_filename", "estimated_word_count", "is_multi_page"],
                limit=1000  # Assuming we don't have more than 1000 entries for now
            )
            
            if not results:
                print("   ⚠️ No data for analysis")
                return
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(results)
            
            # Year distribution
            if 'year' in df.columns:
                year_counts = df['year'].value_counts().sort_index()
                print(f"\n   📅 Year Distribution:")
                for year, count in year_counts.items():
                    print(f"      {year}: {count} questions")
            
            # Marks distribution
            if 'marks_allocated' in df.columns:
                marks_counts = df['marks_allocated'].value_counts()
                print(f"\n   🎯 Marks Distribution:")
                for marks, count in marks_counts.items():
                    print(f"      {marks} marks: {count} questions")
            
            # PDF distribution
            if 'pdf_filename' in df.columns:
                pdf_counts = df['pdf_filename'].value_counts()
                print(f"\n   📄 PDF Distribution:")
                for pdf, count in pdf_counts.items():
                    print(f"      {pdf}: {count} questions")
            
            # Multi-page distribution
            if 'is_multi_page' in df.columns:
                multipage_counts = df['is_multi_page'].value_counts()
                print(f"\n   📄 Multi-page Distribution:")
                for is_multi, count in multipage_counts.items():
                    print(f"      Multi-page: {is_multi}: {count} questions")
            
            # Word count statistics
            if 'estimated_word_count' in df.columns:
                word_stats = df['estimated_word_count'].describe()
                print(f"\n   📊 Word Count Statistics:")
                print(f"      Mean: {word_stats['mean']:.1f} words")
                print(f"      Min: {word_stats['min']:.0f} words")
                print(f"      Max: {word_stats['max']:.0f} words")
                print(f"      Median: {word_stats['50%']:.1f} words")
                
        except Exception as e:
            print(f"❌ Error analyzing data distribution: {e}")
    
    def load_search_model(self):
        """Load BGE model for search testing"""
        if self.embedding_model is None:
            print(f"📥 Loading BGE model for search...")
            try:
                self.embedding_model = SentenceTransformer("BAAI/bge-large-en-v1.5")
                print(f"✅ BGE model loaded")
            except Exception as e:
                print(f"❌ Failed to load BGE model: {e}")
                return False
        return True
    
    def test_search(self, collection: Collection, query: str, limit: int = 3):
        """Test search functionality"""
        print(f"\n🔍 Testing search with query: '{query}'")
        
        if not self.load_search_model():
            return
        
        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode([query], normalize_embeddings=True)
            
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
                limit=limit,
                output_fields=["question_text", "answer_text", "pdf_filename", "question_number", "marks_allocated", "estimated_word_count"]
            )
            
            print(f"📊 Search Results:")
            for i, result in enumerate(results[0], 1):
                print(f"\n   🏆 Rank {i} (Score: {result.score:.4f})")
                print(f"      📄 PDF: {result.entity.get('pdf_filename', 'N/A')}")
                print(f"      📝 Q{result.entity.get('question_number', 'N/A')} ({result.entity.get('marks_allocated', 'N/A')} marks)")
                print(f"      📊 Words: {result.entity.get('estimated_word_count', 'N/A')}")
                
                question = result.entity.get('question_text', 'N/A')
                if len(question) > 100:
                    question = question[:100] + "..."
                print(f"      ❓ Question: {question}")
                
                answer = result.entity.get('answer_text', 'N/A')
                if len(answer) > 150:
                    answer = answer[:150] + "..."
                print(f"      📝 Answer: {answer}")
                
        except Exception as e:
            print(f"❌ Error during search: {e}")
    
    def export_sample_data(self, collection: Collection, output_file: str = "milvus_sample_data.json"):
        """Export sample data to JSON file"""
        print(f"\n💾 Exporting sample data to {output_file}...")
        
        try:
            # Get field names (excluding vector field)
            field_names = [field.name for field in collection.schema.fields 
                          if field.dtype.name != 'FLOAT_VECTOR' and not field.auto_id]
            
            # Query sample data
            results = collection.query(
                expr="",
                output_fields=field_names,
                limit=10  # Export first 10 entries as sample
            )
            
            if results:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Exported {len(results)} entries to {output_file}")
            else:
                print("⚠️ No data to export")
                
        except Exception as e:
            print(f"❌ Error exporting data: {e}")
    
    def run_inspection(self, collection_name: str):
        """Run complete inspection"""
        print("🚀 Starting Milvus Database Inspection...")
        
        try:
            # Connect to database
            self.connect_milvus()
            
            # List all collections
            collections = self.list_collections()
            
            # If specific collection requested, inspect it
            if collection_name:
                if collection_name in collections:
                    collection = self.inspect_collection(collection_name)
                    
                    if collection:
                        # Sample data
                        self.sample_data(collection, limit=3)
                        
                        # Show distribution
                        self.show_data_distribution(collection)
                        
                        # Test search
                        test_queries = [
                            "fiscal policy",
                            "digitization",
                            "subsidy",
                            "land records"
                        ]
                        
                        for query in test_queries:
                            self.test_search(collection, query, limit=2)
                        
                        # Export sample
                        self.export_sample_data(collection)
                        
                else:
                    print(f"❌ Collection '{collection_name}' not found")
                    print(f"Available collections: {collections}")
            
            print(f"\n🎉 Inspection complete!")
            
        except Exception as e:
            print(f"❌ Inspection failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Inspect Milvus database contents")
    parser.add_argument("--collection_name", default="toppers_qa_aayushi_bge", help="Collection name to inspect")
    parser.add_argument("--milvus_db_path", default="./milvus_toppers.db", help="Milvus Lite database path")
    
    args = parser.parse_args()
    
    inspector = MilvusInspector(args.milvus_db_path)
    inspector.run_inspection(args.collection_name)

if __name__ == "__main__":
    main()
