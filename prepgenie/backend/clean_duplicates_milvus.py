#!/usr/bin/env python3
"""
Clean Duplicate Entries from Milvus Collection
============================================

This script removes duplicate entries from the Milvus collection,
keeping only one instance of each unique question.
"""

from pymilvus import connections, Collection, utility
import pandas as pd
from collections import defaultdict

def clean_duplicates():
    """Clean duplicate entries from Milvus collection"""
    
    print("🧹 Cleaning Duplicate Entries from Milvus...")
    
    try:
        # Connect to Milvus Lite
        connections.connect("default", uri="./milvus_toppers.db")
        print("✅ Connected to Milvus Lite")
        
        collection_name = "toppers_qa_aayushi_bge"
        collection = Collection(collection_name)
        collection.load()
        
        print(f"📊 Collection: {collection_name}")
        print(f"📈 Total entities before cleanup: {collection.num_entities}")
        
        # Get all data with IDs for deletion
        results = collection.query(
            expr="",
            output_fields=["id", "question_text", "pdf_filename", "question_number", "marks_allocated", "estimated_word_count"],
            limit=200
        )
        
        print(f"📋 Retrieved {len(results)} records for analysis")
        
        # Find duplicates and identify which IDs to keep/delete
        seen_combinations = set()
        ids_to_keep = []
        ids_to_delete = []
        
        for record in results:
            # Create unique identifier
            unique_key = (
                record['pdf_filename'],
                record['question_number'],
                record['marks_allocated'],
                record['estimated_word_count']
            )
            
            if unique_key not in seen_combinations:
                # First occurrence - keep it
                seen_combinations.add(unique_key)
                ids_to_keep.append(record['id'])
            else:
                # Duplicate - mark for deletion
                ids_to_delete.append(record['id'])
        
        print(f"\n📊 DUPLICATE ANALYSIS:")
        print(f"   📈 Total records: {len(results)}")
        print(f"   ✅ Unique records to keep: {len(ids_to_keep)}")
        print(f"   🗑️ Duplicate records to delete: {len(ids_to_delete)}")
        
        if ids_to_delete:
            print(f"\n🗑️ Deleting {len(ids_to_delete)} duplicate entries...")
            
            # Delete duplicates in batches
            batch_size = 50
            deleted_count = 0
            
            for i in range(0, len(ids_to_delete), batch_size):
                batch_ids = ids_to_delete[i:i + batch_size]
                
                # Create expression for batch deletion
                id_list_str = ",".join(map(str, batch_ids))
                delete_expr = f"id in [{id_list_str}]"
                
                try:
                    result = collection.delete(delete_expr)
                    deleted_count += len(batch_ids)
                    print(f"   🗑️ Deleted batch {i//batch_size + 1}: {len(batch_ids)} records")
                except Exception as e:
                    print(f"   ❌ Error deleting batch {i//batch_size + 1}: {e}")
            
            # Flush changes to disk
            collection.flush()
            print(f"✅ Flushed changes to disk")
            
            print(f"\n📊 CLEANUP COMPLETE:")
            print(f"   🗑️ Total deleted: {deleted_count}")
            print(f"   📈 Remaining entities: {collection.num_entities}")
            
        else:
            print(f"✅ No duplicates found to delete!")
        
        # Verify final state
        final_count = collection.num_entities
        print(f"\n🎯 FINAL STATE:")
        print(f"   📊 Total entities: {final_count}")
        print(f"   ✅ Expected unique questions: 60")
        
        if final_count == 60:
            print(f"   ✅ Perfect! Database now contains exactly 60 unique questions")
        else:
            print(f"   ⚠️ Warning: Expected 60, but have {final_count} entities")
            
    except Exception as e:
        print(f"❌ Error cleaning duplicates: {e}")

if __name__ == "__main__":
    clean_duplicates()
