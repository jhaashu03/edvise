"""
Check Milvus Database Contents
Inspect what collections and data exist in the local Milvus database
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pymilvus import connections, utility, Collection
from app.services.topper_vector_service import TopperVectorService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def inspect_milvus_database():
    """Inspect the Milvus database contents"""
    
    print("🔍 MILVUS DATABASE INSPECTION")
    print("=" * 50)
    
    try:
        # Connect to local Milvus
        print("🔗 Connecting to local Milvus...")
        connections.connect(
            alias="inspect",
            uri="./milvus_lite_local.db"
        )
        print("✅ Connected to local Milvus database")
        
        # List all collections
        collections = utility.list_collections(using="inspect")
        print(f"\n📊 Found {len(collections)} collections:")
        
        for i, collection_name in enumerate(collections, 1):
            print(f"   {i}. {collection_name}")
            
            try:
                # Get collection info
                collection = Collection(collection_name, using="inspect")
                collection.load()
                
                # Get count
                count = collection.num_entities
                print(f"      📈 Records: {count}")
                
                # Get schema info
                schema = collection.schema
                print(f"      📋 Fields: {len(schema.fields)}")
                for field in schema.fields:
                    print(f"         - {field.name} ({field.dtype})")
                
                # If there's data, show a sample
                if count > 0:
                    print(f"      🔍 Sample data from {collection_name}:")
                    
                    # Query a few records
                    results = collection.query(
                        expr="",  # Empty expression gets all
                        output_fields=["*"],
                        limit=3
                    )
                    
                    for j, record in enumerate(results[:2], 1):  # Show first 2 records
                        print(f"         Record {j}:")
                        for key, value in record.items():
                            if key != "embedding":  # Skip embedding vector for readability
                                if isinstance(value, str) and len(value) > 100:
                                    print(f"           {key}: {value[:100]}...")
                                else:
                                    print(f"           {key}: {value}")
                print()
                
            except Exception as e:
                print(f"      ❌ Error inspecting {collection_name}: {e}")
                print()
        
        # Disconnect
        connections.disconnect("inspect")
        
        print("🎯 INSPECTION COMPLETE!")
        
        if len(collections) == 0:
            print("❌ No collections found in database")
            print("💡 This means no data has been stored yet")
        else:
            total_records = 0
            for collection_name in collections:
                try:
                    connections.connect(alias="count", uri="./milvus_lite_local.db")
                    collection = Collection(collection_name, using="count")
                    collection.load()
                    total_records += collection.num_entities
                    connections.disconnect("count")
                except:
                    pass
            
            print(f"📊 Total records across all collections: {total_records}")
        
    except Exception as e:
        logger.error(f"❌ Failed to inspect database: {e}")

async def check_topper_service_collections():
    """Check if topper service has created its collections"""
    
    print("\n🎯 CHECKING TOPPER SERVICE COLLECTIONS")
    print("=" * 50)
    
    try:
        # Initialize vector service
        os.environ['ENVIRONMENT'] = 'local'
        os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
        
        vector_service = TopperVectorService()
        await vector_service.initialize()
        
        print("✅ Topper vector service initialized")
        
        # Check collection stats
        try:
            stats = await vector_service.get_collection_stats()
            print(f"📊 Collection Stats:")
            for key, value in stats.items():
                print(f"   {key}: {value}")
        except Exception as e:
            print(f"❌ Could not get collection stats: {e}")
        
        # Try a simple search to see if data exists
        try:
            results = await vector_service.search_similar_topper_answers(
                query_question="test query",
                limit=1
            )
            print(f"🔍 Search test returned {len(results)} results")
            if results:
                print("✅ Data is accessible via search")
                print(f"   Sample result: {results[0].get('topper_name', 'Unknown')}")
            else:
                print("❌ No data returned from search")
        except Exception as e:
            print(f"❌ Search test failed: {e}")
            
    except Exception as e:
        print(f"❌ Failed to check topper service: {e}")

async def main():
    """Main inspection function"""
    
    # Check if database file exists
    db_path = Path("./milvus_lite_local.db")
    if not db_path.exists():
        print("❌ Local Milvus database file not found!")
        print(f"   Expected location: {db_path.absolute()}")
        return
    
    print(f"✅ Found database file: {db_path.absolute()}")
    print(f"📁 File size: {db_path.stat().st_size / 1024:.2f} KB")
    
    # Inspect database contents
    await inspect_milvus_database()
    
    # Check topper service
    await check_topper_service_collections()

if __name__ == "__main__":
    asyncio.run(main())
