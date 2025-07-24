#!/usr/bin/env python3
"""
Milvus Lite Browser - A tool to browse and inspect the vector database
"""
import asyncio
import json
import logging
import os
from typing import List, Dict, Any, Optional
from pymilvus import connections, Collection, utility
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MilvusBrowser:
    def __init__(self, db_path: str = "./milvus_lite_local.db"):
        self.db_path = db_path
        self.connection_alias = "default"
        self.connected = False
        
    def connect(self):
        """Connect to Milvus Lite database"""
        try:
            # For Milvus Lite, just use the file path directly
            connections.connect(
                alias=self.connection_alias,
                uri=os.path.abspath(self.db_path)
            )
            self.connected = True
            print(f"✅ Connected to Milvus Lite at {self.db_path}")
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """List all collections in the database"""
        if not self.connected:
            self.connect()
        
        collections = utility.list_collections()
        return collections
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a collection"""
        if not self.connected:
            self.connect()
        
        if not utility.has_collection(collection_name):
            return {"error": f"Collection '{collection_name}' does not exist"}
        
        collection = Collection(collection_name)
        collection.load()
        
        return {
            "name": collection_name,
            "description": collection.description,
            "total_entities": collection.num_entities,
            "schema": collection.schema,
            "fields": [
                {
                    "name": field.name,
                    "type": str(field.dtype),
                    "description": field.description,
                    "is_primary": field.is_primary,
                    "auto_id": field.auto_id,
                    "params": field.params if hasattr(field, 'params') else None
                }
                for field in collection.schema.fields
            ]
        }
    
    def query_collection(
        self, 
        collection_name: str, 
        limit: int = 10, 
        offset: int = 0,
        expr: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query collection and return results"""
        if not self.connected:
            self.connect()
        
        if not utility.has_collection(collection_name):
            return []
        
        collection = Collection(collection_name)
        collection.load()
        
        # Get all field names except the vector field
        output_fields = [
            field.name for field in collection.schema.fields 
            if field.dtype.name not in ['FLOAT_VECTOR', 'BINARY_VECTOR']
        ]
        
        try:
            # Query with pagination
            if expr:
                results = collection.query(
                    expr=expr,
                    output_fields=output_fields,
                    limit=limit,
                    offset=offset
                )
            else:
                # If no expression, get all records with pagination
                # Since Milvus requires an expression, we'll use a broad one
                results = collection.query(
                    expr="id >= 0",  # Get all records with non-negative IDs
                    output_fields=output_fields,
                    limit=limit,
                    offset=offset
                )
            
            return results
        except Exception as e:
            print(f"❌ Query failed: {e}")
            return []
    
    def search_similar(
        self, 
        collection_name: str, 
        query_text: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors using text query"""
        if not self.connected:
            self.connect()
        
        if not utility.has_collection(collection_name):
            return []
        
        collection = Collection(collection_name)
        collection.load()
        
        # Generate embedding for the query
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_embedding = model.encode(query_text, normalize_embeddings=True).tolist()
        
        # Get output fields (exclude vector field)
        output_fields = [
            field.name for field in collection.schema.fields 
            if field.dtype.name not in ['FLOAT_VECTOR', 'BINARY_VECTOR']
        ]
        
        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": 10}
        }
        
        try:
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=limit,
                output_fields=output_fields
            )
            
            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "id": hit.id,
                        "distance": hit.distance,
                        "score": 1 - hit.distance,  # Convert distance to similarity score
                    }
                    # Add all the entity fields
                    result.update(hit.entity.value)
                    formatted_results.append(result)
            
            return formatted_results
        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection (use with caution!)"""
        if not self.connected:
            self.connect()
        
        try:
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                print(f"✅ Deleted collection: {collection_name}")
                return True
            else:
                print(f"❌ Collection '{collection_name}' does not exist")
                return False
        except Exception as e:
            print(f"❌ Failed to delete collection: {e}")
            return False


def main():
    """Interactive Milvus browser"""
    print("🔍 Milvus Lite Database Browser")
    print("=" * 50)
    
    browser = MilvusBrowser()
    
    try:
        browser.connect()
        
        while True:
            print(f"\\n📋 Available commands:")
            print("1. List collections")
            print("2. Collection info")
            print("3. Query collection")
            print("4. Search similar")
            print("5. Delete collection")
            print("6. Exit")
            
            choice = input("\\nEnter your choice (1-6): ").strip()
            
            if choice == "1":
                print("\\n📚 Collections:")
                collections = browser.list_collections()
                if collections:
                    for i, col in enumerate(collections, 1):
                        print(f"   {i}. {col}")
                else:
                    print("   No collections found")
            
            elif choice == "2":
                collections = browser.list_collections()
                if not collections:
                    print("❌ No collections found")
                    continue
                
                print("\\n📚 Available collections:")
                for i, col in enumerate(collections, 1):
                    print(f"   {i}. {col}")
                
                col_choice = input("Enter collection number: ").strip()
                try:
                    col_idx = int(col_choice) - 1
                    if 0 <= col_idx < len(collections):
                        col_name = collections[col_idx]
                        info = browser.get_collection_info(col_name)
                        print(f"\\n📊 Collection '{col_name}' Info:")
                        print(json.dumps(info, indent=2, default=str))
                    else:
                        print("❌ Invalid collection number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "3":
                collections = browser.list_collections()
                if not collections:
                    print("❌ No collections found")
                    continue
                
                print("\\n📚 Available collections:")
                for i, col in enumerate(collections, 1):
                    print(f"   {i}. {col}")
                
                col_choice = input("Enter collection number: ").strip()
                try:
                    col_idx = int(col_choice) - 1
                    if 0 <= col_idx < len(collections):
                        col_name = collections[col_idx]
                        
                        limit = input("Number of records to fetch (default 10): ").strip()
                        limit = int(limit) if limit else 10
                        
                        offset = input("Offset (default 0): ").strip()
                        offset = int(offset) if offset else 0
                        
                        results = browser.query_collection(col_name, limit=limit, offset=offset)
                        
                        print(f"\\n📄 Query Results ({len(results)} records):")
                        for i, record in enumerate(results, 1):
                            print(f"\\n--- Record {i} ---")
                            for key, value in record.items():
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"{key}: {value[:100]}...")
                                else:
                                    print(f"{key}: {value}")
                    else:
                        print("❌ Invalid collection number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "4":
                collections = browser.list_collections()
                if not collections:
                    print("❌ No collections found")
                    continue
                
                print("\\n📚 Available collections:")
                for i, col in enumerate(collections, 1):
                    print(f"   {i}. {col}")
                
                col_choice = input("Enter collection number: ").strip()
                try:
                    col_idx = int(col_choice) - 1
                    if 0 <= col_idx < len(collections):
                        col_name = collections[col_idx]
                        
                        query_text = input("Enter search query: ").strip()
                        if not query_text:
                            print("❌ Query cannot be empty")
                            continue
                        
                        limit = input("Number of results (default 5): ").strip()
                        limit = int(limit) if limit else 5
                        
                        print(f"\\n🔍 Searching for: '{query_text}'...")
                        results = browser.search_similar(col_name, query_text, limit=limit)
                        
                        print(f"\\n🎯 Search Results ({len(results)} found):")
                        for i, result in enumerate(results, 1):
                            print(f"\\n--- Result {i} (Score: {result.get('score', 'N/A'):.3f}) ---")
                            for key, value in result.items():
                                if key in ['distance', 'score']:
                                    continue
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"{key}: {value[:100]}...")
                                else:
                                    print(f"{key}: {value}")
                    else:
                        print("❌ Invalid collection number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "5":
                collections = browser.list_collections()
                if not collections:
                    print("❌ No collections found")
                    continue
                
                print("\\n📚 Available collections:")
                for i, col in enumerate(collections, 1):
                    print(f"   {i}. {col}")
                
                col_choice = input("Enter collection number: ").strip()
                try:
                    col_idx = int(col_choice) - 1
                    if 0 <= col_idx < len(collections):
                        col_name = collections[col_idx]
                        
                        confirm = input(f"⚠️  Are you sure you want to delete '{col_name}'? (yes/no): ").strip().lower()
                        if confirm == "yes":
                            browser.delete_collection(col_name)
                        else:
                            print("❌ Deletion cancelled")
                    else:
                        print("❌ Invalid collection number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "6":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-6.")
    
    except KeyboardInterrupt:
        print("\\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
