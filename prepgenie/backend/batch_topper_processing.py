"""
Batch Topper Processing Script
Processes topper PDFs in batches to avoid overwhelming the system
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from topper_pdf_processing_pipeline import TopperPDFProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'batch_processing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def process_in_batches(batch_size: int = 5):
    """Process topper PDFs in batches"""
    
    logger.info(f"🚀 Starting Batch Processing (batch size: {batch_size})")
    logger.info("=" * 60)
    
    processor = TopperPDFProcessor()
    
    if not await processor.initialize():
        logger.error("❌ Failed to initialize - stopping")
        return
    
    # Discover all PDFs
    pdf_files = await processor.discover_topper_pdfs()
    
    if not pdf_files:
        logger.error("❌ No PDF files found")
        return
    
    logger.info(f"📚 Found {len(pdf_files)} PDFs to process in {(len(pdf_files) + batch_size - 1) // batch_size} batches")
    
    # Process in batches
    total_processed = 0
    total_failed = 0
    
    for batch_num in range(0, len(pdf_files), batch_size):
        batch_files = pdf_files[batch_num:batch_num + batch_size]
        batch_index = (batch_num // batch_size) + 1
        
        logger.info(f"\n📦 Processing Batch {batch_index}: {len(batch_files)} files")
        logger.info("-" * 40)
        
        batch_processed = 0
        batch_failed = 0
        
        for pdf_file in batch_files:
            logger.info(f"🔄 Processing: {os.path.basename(pdf_file)}")
            
            success = await processor.process_single_pdf(pdf_file)
            
            if success:
                batch_processed += 1
                total_processed += 1
                logger.info(f"✅ Success - {os.path.basename(pdf_file)}")
            else:
                batch_failed += 1
                total_failed += 1
                logger.error(f"❌ Failed - {os.path.basename(pdf_file)}")
        
        logger.info(f"\n📊 Batch {batch_index} Summary:")
        logger.info(f"   ✅ Successful: {batch_processed}")
        logger.info(f"   ❌ Failed: {batch_failed}")
        logger.info(f"   📈 Total so far: {total_processed} successful, {total_failed} failed")
        
        # Brief pause between batches
        if batch_num + batch_size < len(pdf_files):
            logger.info("⏸️ Brief pause before next batch...")
            await asyncio.sleep(2)
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 BATCH PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"✅ Total successful: {total_processed}")
    logger.info(f"❌ Total failed: {total_failed}")
    logger.info(f"📊 Success rate: {(total_processed / len(pdf_files) * 100):.1f}%")
    
    # Vector database final stats
    try:
        stats = await processor.vector_service.get_collection_stats()
        logger.info(f"🔢 Final Vector DB Stats: {stats}")
    except Exception as e:
        logger.error(f"Could not get final vector stats: {e}")
    
    await processor.cleanup()
    logger.info("🧹 Processing complete!")

async def quick_process_top_n(n: int = 3):
    """Process just the first N PDFs for quick testing"""
    
    logger.info(f"🧪 Quick Processing - Top {n} PDFs")
    logger.info("-" * 40)
    
    processor = TopperPDFProcessor()
    
    if not await processor.initialize():
        logger.error("❌ Failed to initialize")
        return
    
    pdf_files = await processor.discover_topper_pdfs()
    
    if not pdf_files:
        logger.error("❌ No PDF files found")
        return
    
    # Process just the first N files
    test_files = pdf_files[:n]
    logger.info(f"Processing {len(test_files)} files for quick test")
    
    for i, pdf_file in enumerate(test_files, 1):
        logger.info(f"\n🔄 Processing {i}/{len(test_files)}: {os.path.basename(pdf_file)}")
        success = await processor.process_single_pdf(pdf_file)
        
        if success:
            logger.info(f"✅ Success!")
        else:
            logger.error(f"❌ Failed!")
    
    # Quick vector search test
    try:
        logger.info("\n🔍 Testing vector search...")
        results = await processor.vector_service.search_similar_topper_answers(
            query_question="Discuss digital governance initiatives in India",
            student_answer="Digital India has transformed governance through technology",
            filters={'exam_year': 2024},
            limit=5
        )
        logger.info(f"✅ Search test: {len(results)} results found")
    except Exception as e:
        logger.error(f"❌ Search test failed: {e}")
    
    await processor.cleanup()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Topper PDF Processing")
    parser.add_argument("--mode", choices=["quick", "batch", "all"], default="quick",
                       help="Processing mode: quick (3 PDFs), batch (batched), all (all at once)")
    parser.add_argument("--batch_size", type=int, default=5,
                       help="Batch size for batch processing")
    parser.add_argument("--quick_count", type=int, default=3,
                       help="Number of PDFs for quick processing")
    
    args = parser.parse_args()
    
    if args.mode == "quick":
        print(f"🧪 Quick Processing Mode - Processing {args.quick_count} PDFs")
        asyncio.run(quick_process_top_n(args.quick_count))
    elif args.mode == "batch":
        print(f"📦 Batch Processing Mode - Batch size: {args.batch_size}")
        asyncio.run(process_in_batches(args.batch_size))
    elif args.mode == "all":
        print("🚀 Full Processing Mode - All PDFs at once")
        from topper_pdf_processing_pipeline import main
        asyncio.run(main())
    
    print("\n✅ Processing complete!")
