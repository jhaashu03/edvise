#!/usr/bin/env python3
"""
Check for Duplicate Entries in Milvus Collection
=============================================

This script checks for potential duplicate entries in the Milvus database
and provides options to clean them up if needed.
"""

from pymilvus import connections, Collection, utility
import pandas as pd
from collections import defaultdict

def check_duplicates():
    """Check for duplicate entries in Milvus collection"""
    
    print("🔍 Checking for Duplicate Entries in Milvus...")
    
    try:
        # Connect to Milvus Lite
        connections.connect("default", uri="./milvus_toppers.db")
        print("✅ Connected to Milvus Lite")
        
        collection_name = "toppers_qa_aayushi_bge"
        collection = Collection(collection_name)
        collection.load()
        
        print(f"📊 Collection: {collection_name}")
        print(f"📈 Total entities: {collection.num_entities}")
        
        # Get all data for duplicate analysis
        results = collection.query(
            expr="",
            output_fields=["question_text", "pdf_filename", "question_number", "marks_allocated", "estimated_word_count", "pages_spanned"],
            limit=200  # Get more than current 120 to be safe
        )
        
        print(f"📋 Retrieved {len(results)} records for analysis")
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(results)
        
        # Check for duplicates based on key fields
        duplicate_groups = defaultdict(list)
        
        for i, row in df.iterrows():
            # Create a unique key based on content
            key = (
                row['pdf_filename'],
                row['question_number'], 
                row['marks_allocated'],
                row['estimated_word_count']
            )
            duplicate_groups[key].append(i)
        
        # Find actual duplicates
        duplicates_found = []
        for key, indices in duplicate_groups.items():
            if len(indices) > 1:
                duplicates_found.append((key, indices))
        
        print(f"\n📊 DUPLICATE ANALYSIS:")
        print(f"   📈 Total records: {len(results)}")
        print(f"   🔍 Unique combinations: {len(duplicate_groups)}")
        print(f"   ⚠️ Duplicate groups found: {len(duplicates_found)}")
        
        if duplicates_found:
            print(f"\n⚠️ DUPLICATE ENTRIES FOUND:")
            for i, (key, indices) in enumerate(duplicates_found[:5], 1):  # Show first 5
                pdf_name, q_num, marks, word_count = key
                print(f"\n   {i}. PDF: {pdf_name}")
                print(f"      Q{q_num} ({marks} marks, {word_count} words)")
                print(f"      Found {len(indices)} times at indices: {indices}")
                
                # Show sample questions for verification
                for idx in indices[:2]:  # Show first 2 instances
                    question_preview = df.iloc[idx]['question_text'][:80] + "..."
                    print(f"         • {question_preview}")
        else:
            print(f"✅ No duplicates found!")
        
        # Show distribution by PDF
        print(f"\n📄 Distribution by PDF:")
        pdf_counts = df['pdf_filename'].value_counts()
        for pdf, count in pdf_counts.items():
            print(f"   • {pdf}: {count} questions")
        
        # Show distribution by marks
        print(f"\n🎯 Distribution by Marks:")
        marks_counts = df['marks_allocated'].value_counts()
        for marks, count in marks_counts.items():
            print(f"   • {marks} marks: {count} questions")
        
        print(f"\n🎯 SUMMARY:")
        expected_total = len(pdf_counts) * 20  # Each PDF should have 20 questions
        print(f"   📊 Expected total: {expected_total} questions")
        print(f"   📊 Actual total: {len(results)} questions")
        
        if len(results) > expected_total:
            print(f"   ⚠️ Found {len(results) - expected_total} extra entries (possible duplicates)")
        elif len(results) == expected_total:
            print(f"   ✅ Total matches expected count")
        else:
            print(f"   ⚠️ Missing {expected_total - len(results)} entries")
            
    except Exception as e:
        print(f"❌ Error checking duplicates: {e}")

if __name__ == "__main__":
    check_duplicates()
