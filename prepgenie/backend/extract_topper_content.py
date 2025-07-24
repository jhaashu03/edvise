#!/usr/bin/env python3
"""
Extract Topper Content from VisionIAS PDF
Processes the existing topper PDF and stores the content for comparison analysis
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.services.topper_content_extractor import topper_content_extractor
from app.models.topper_reference import TopperReference

# Configuration
PDF_PATH = "/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/docs/VisionIAS Toppers Answer Booklet Shakti Dubey.pdf"
TOPPER_NAME = "Shakti Dubey"
INSTITUTE = "VisionIAS"
EXAM_YEAR = 2023  # Assumed
RANK = 1  # Assumed - can be updated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("topper_extraction")

async def main():
    """
    Extract topper content from the VisionIAS PDF and store in database
    """
    
    print("🎯 UPSC Topper Content Extraction")
    print("=" * 50)
    print(f"📄 Processing: {PDF_PATH}")
    print(f"👤 Topper: {TOPPER_NAME}")
    print(f"🏛️ Institute: {INSTITUTE}")
    print("=" * 50)
    
    # Check if PDF exists
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: PDF file not found at {PDF_PATH}")
        return
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Step 1: Extract topper content from PDF
        print("\n🔍 Step 1: Extracting content from PDF...")
        extraction_result = await topper_content_extractor.extract_topper_content_from_pdf(
            pdf_path=PDF_PATH,
            topper_name=TOPPER_NAME,
            institute=INSTITUTE,
            exam_year=EXAM_YEAR,
            rank=RANK
        )
        
        if not extraction_result["success"]:
            print(f"❌ Extraction failed: {extraction_result.get('error', 'Unknown error')}")
            return
        
        topper_references = extraction_result["topper_references"]
        print(f"✅ Extracted {len(topper_references)} question-answer pairs")
        
        # Show summary of extracted content
        print(f"\n📊 Extraction Summary:")
        subjects = {}
        total_words = 0
        
        for ref in topper_references:
            subject = ref.subject
            if subject not in subjects:
                subjects[subject] = {"count": 0, "marks": 0}
            subjects[subject]["count"] += 1
            subjects[subject]["marks"] += ref.marks
            total_words += ref.word_count or 0
        
        for subject, data in subjects.items():
            print(f"   {subject}: {data['count']} questions, {data['marks']} total marks")
        
        print(f"   Total words: {total_words:,}")
        
        # Step 2: Save to database
        print(f"\n💾 Step 2: Saving to database...")
        save_result = await topper_content_extractor.save_topper_references(
            topper_references=topper_references,
            db=db
        )
        
        print(f"✅ Saved {save_result['saved_count']}/{save_result['total_references']} references")
        
        if save_result['errors']:
            print(f"⚠️ Errors: {len(save_result['errors'])}")
            for error in save_result['errors'][:3]:  # Show first 3 errors
                print(f"   - {error}")
        
        # Step 3: Extract and save patterns
        print(f"\n🔍 Step 3: Extracting topper patterns...")
        
        # Get saved references from database
        saved_refs = db.query(TopperReference).filter(
            TopperReference.topper_name == TOPPER_NAME
        ).all()
        
        if saved_refs:
            pattern_result = await topper_content_extractor.extract_and_save_topper_patterns(
                topper_references=saved_refs,
                db=db
            )
            
            if pattern_result["success"]:
                print(f"✅ Extracted {pattern_result['patterns_extracted']} patterns")
                print(f"💾 Saved {pattern_result['patterns_saved']} patterns to database")
                print(f"📚 Subjects analyzed: {', '.join(pattern_result['subjects_analyzed'])}")
            else:
                print(f"⚠️ Pattern extraction failed: {pattern_result.get('error', 'Unknown error')}")
        else:
            print("⚠️ No saved references found for pattern extraction")
        
        # Step 4: Verification
        print(f"\n✅ Step 4: Verification")
        total_refs = db.query(TopperReference).count()
        topper_refs_count = db.query(TopperReference).filter(
            TopperReference.topper_name == TOPPER_NAME
        ).count()
        
        print(f"📊 Database now contains:")
        print(f"   Total topper references: {total_refs}")
        print(f"   {TOPPER_NAME}'s answers: {topper_refs_count}")
        
        print(f"\n🎉 Topper content extraction completed successfully!")
        print(f"📈 The 14th dimension (Topper Comparison) is now ready to use!")
        
        # Show first example
        if saved_refs:
            first_ref = saved_refs[0]
            print(f"\n🔍 Example extracted content:")
            print(f"Subject: {first_ref.subject}")
            print(f"Question: {first_ref.question_text[:100]}...")
            print(f"Answer length: {len(first_ref.topper_answer_text)} characters")
            if first_ref.answer_analysis:
                print(f"Analysis available: {len(first_ref.answer_analysis)} pattern categories")
        
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting topper content extraction...")
    asyncio.run(main())
