#!/usr/bin/env python3
"""
Milvus Connection Validation Script
Validates connection to Zilliz Cloud and lists existing collections
"""

import os
import sys
import logging
from typing import List, Dict, Any
from pymilvus import connections, utility, Collection

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MilvusValidator:
    def __init__(self, uri: str, token: str):
        self.uri = uri
        self.token = token
        self.connection_alias = "validation"
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to Milvus using provided credentials"""
        try:
            logger.info(f"🔗 Connecting to Milvus at: {self.uri}")
            
            connections.connect(
                alias=self.connection_alias,
                uri=self.uri,
                token=self.token
            )
            
            self.connected = True
            logger.info("✅ Successfully connected to Milvus!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
    
    def list_collections(self) -> List[str]:
        """List all collections in the database"""
        if not self.connected:
            logger.error("❌ Not connected to Milvus")
            return []
        
        try:
            collections = utility.list_collections()
            logger.info(f"📚 Found {len(collections)} collections:")
            
            for i, collection_name in enumerate(collections, 1):
                logger.info(f"   {i}. {collection_name}")
            
            return collections
            
        except Exception as e:
            logger.error(f"❌ Failed to list collections: {e}")
            return []
    
    def get_collection_details(self, collection_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific collection"""
        if not self.connected:
            logger.error("❌ Not connected to Milvus")
            return {}
        
        try:
            if not utility.has_collection(collection_name):
                logger.warning(f"⚠️ Collection '{collection_name}' does not exist")
                return {}
            
            collection = Collection(collection_name)
            
            # Get basic info
            info = {
                'name': collection_name,
                'description': collection.description,
                'num_entities': collection.num_entities,
                'schema': {
                    'fields': [],
                    'description': collection.schema.description
                }
            }
            
            # Get field information
            for field in collection.schema.fields:
                field_info = {
                    'name': field.name,
                    'type': str(field.dtype),
                    'is_primary': field.is_primary,
                    'auto_id': field.auto_id,
                    'description': field.description
                }
                
                # Add dimension info for vector fields
                if hasattr(field, 'params') and 'dim' in field.params:
                    field_info['dimension'] = field.params['dim']
                
                info['schema']['fields'].append(field_info)
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Failed to get collection details for '{collection_name}': {e}")
            return {}
    
    def validate_connection_comprehensive(self):
        """Run comprehensive validation of the Milvus connection"""
        logger.info("🔍 Starting Comprehensive Milvus Validation")
        logger.info("=" * 60)
        
        # Step 1: Test connection
        if not self.connect():
            return False
        
        # Step 2: List collections
        collections = self.list_collections()
        
        if not collections:
            logger.info("📝 No collections found - this is normal for a new database")
            logger.info("✅ Connection is valid and ready for new collections")
            return True
        
        # Step 3: Examine each collection
        logger.info("\n📊 Collection Details:")
        logger.info("-" * 40)
        
        for collection_name in collections:
            logger.info(f"\n🗂️ Collection: {collection_name}")
            details = self.get_collection_details(collection_name)
            
            if details:
                logger.info(f"   📈 Entities: {details['num_entities']:,}")
                logger.info(f"   📝 Description: {details.get('description', 'N/A')}")
                logger.info(f"   🔧 Fields:")
                
                for field in details['schema']['fields']:
                    field_str = f"      • {field['name']} ({field['type']})"
                    if field['is_primary']:
                        field_str += " [PRIMARY]"
                    if field.get('dimension'):
                        field_str += f" [DIM: {field['dimension']}]"
                    logger.info(field_str)
        
        logger.info("\n✅ Validation Complete!")
        return True
    
    def disconnect(self):
        """Clean up connection"""
        try:
            if self.connected:
                connections.disconnect(self.connection_alias)
                logger.info("🔌 Disconnected from Milvus")
        except Exception as e:
            logger.warning(f"⚠️ Error during disconnect: {e}")

def main():
    """Main validation function"""
    
    # Your provided credentials
    milvus_uri = "https://in03-7399fcefb79acf1.serverless.gcp-us-west1.cloud.zilliz.com"
    milvus_token = "9dd75ac2787c2074903f7fa3fae78a762482ddd693d8431c975f7ae52c154eabd11d4b6468481036f8a9940b4e1cff72313a4169"
    
    print("🎯 Milvus Connection Validation")
    print("=" * 50)
    print(f"🔗 Endpoint: {milvus_uri}")
    print(f"🔑 Token: {milvus_token[:20]}...{milvus_token[-10:]}")
    print("-" * 50)
    
    validator = MilvusValidator(milvus_uri, milvus_token)
    
    try:
        success = validator.validate_connection_comprehensive()
        
        if success:
            print("\n🎉 VALIDATION RESULT: SUCCESS!")
            print("✅ Your Milvus credentials are valid and working")
            print("✅ Connection established successfully")
            print("✅ Ready for topper vector processing")
        else:
            print("\n❌ VALIDATION RESULT: FAILED!")
            print("❌ Please check your credentials and network connection")
            
    except KeyboardInterrupt:
        print("\n⏹️ Validation interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
    finally:
        validator.disconnect()

if __name__ == "__main__":
    main()
