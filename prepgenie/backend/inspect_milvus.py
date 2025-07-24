#!/usr/bin/env python3
"""
Quick Milvus Lite inspection script
"""
import asyncio
import json
from browse_milvus import MilvusBrowser

def quick_inspect():
    """Quick inspection of the Milvus Lite database"""
    print("🔍 Quick Milvus Lite Database Inspection")
    print("=" * 50)
    
    browser = MilvusBrowser()
    browser.connect()
    
    # List all collections
    collections = browser.list_collections()
    print(f"\\n📚 Collections: {len(collections)}")
    
    for col_name in collections:
        print(f"\\n🗂️  Collection: {col_name}")
        print("-" * 30)
        
        # Get collection info
        info = browser.get_collection_info(col_name)
        print(f"Total entities: {info.get('total_entities', 0)}")
        print(f"Description: {info.get('description', 'N/A')}")
        
        # Show schema
        print("\\nFields:")
        for field in info.get('fields', []):
            field_info = f"  • {field['name']} ({field['type']})"
            if field['is_primary']:
                field_info += " [PRIMARY]"
            if field.get('auto_id'):
                field_info += " [AUTO_ID]"
            print(field_info)
        
        # Show sample records
        print("\\n📄 Sample Records:")
        results = browser.query_collection(col_name, limit=3)
        
        for i, record in enumerate(results[:3], 1):
            print(f"\\n  Record {i}:")
            for key, value in record.items():
                if isinstance(value, str) and len(value) > 80:
                    print(f"    {key}: {value[:80]}...")
                else:
                    print(f"    {key}: {value}")
    
    print(f"\\n✅ Inspection complete!")

if __name__ == "__main__":
    quick_inspect()
