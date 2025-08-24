#!/usr/bin/env python3
"""
Quick Milvus Entry Count Check
=============================

This script quickly checks the number of entries in the Milvus database.
"""

from pymilvus import connections, Collection, utility

def check_milvus_entries():
    """Check number of entries in Milvus database"""
    
    print("🔍 Checking Milvus Database Entries...")
    
    try:
        # Connect to Milvus Lite
        connections.connect("default", uri="./milvus_toppers.db")
        print("✅ Connected to Milvus Lite")
        
        # List all collections
        collections = utility.list_collections()
        print(f"📊 Found {len(collections)} collection(s): {collections}")
        
        total_entries = 0
        
        for collection_name in collections:
            collection = Collection(collection_name)
            collection.load()
            
            count = collection.num_entities
            total_entries += count
            
            print(f"📁 Collection '{collection_name}': {count:,} entries")
            
            # Get some basic stats
            print(f"   🏗️ Schema fields: {len(collection.schema.fields)}")
            print(f"   🔍 Indexes: {len(collection.indexes)}")
            
        print(f"\n🎯 TOTAL ENTRIES: {total_entries:,}")
        
        if total_entries > 0:
            print(f"✅ Database contains data and is ready for use")
        else:
            print(f"⚠️ Database is empty")
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_milvus_entries()
