"""
Process One PDF and Store in Zilliz Cloud
Extract content from a single topper PDF and store it in the remote Zilliz database
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.services.topper_vector_service import TopperVectorService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZillizTopperProcessor:
    """Process single PDF and store in Zilliz Cloud"""
    
    def __init__(self):
        self.toppers_directory = "/Users/a0j0agc/Desktop/Personal/ToppersCopy/2024/"
        # Force use of remote Zilliz instead of local
        os.environ['ENVIRONMENT'] = 'production'  # This will use Zilliz Cloud
        os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
        
    async def initialize_zilliz_service(self):
        """Initialize vector service to use Zilliz Cloud"""
        try:
            logger.info("🔧 Initializing Zilliz Cloud Vector Service...")
            
            # Initialize vector service in production mode (uses Zilliz)
            self.vector_service = TopperVectorService()
            # Force remote connection
            self.vector_service.use_local = False
            
            await self.vector_service.initialize()
            
            logger.info("✅ Zilliz Cloud vector service initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Zilliz service: {e}")
            return False
    
    async def process_single_pdf_to_zilliz(self, pdf_filename: str):
        """Process a specific PDF and store in Zilliz"""
        
        pdf_path = os.path.join(self.toppers_directory, pdf_filename)
        if not os.path.exists(pdf_path):
            logger.error(f"❌ PDF not found: {pdf_path}")
            return False
        
        logger.info(f"📄 Processing {pdf_filename} for Zilliz Cloud storage...")
        
        try:
            # Extract topper info from filename
            topper_name = pdf_filename.replace("VisionIAS Toppers Answer Booklet", "").replace(".pdf", "").strip()
            topper_name = topper_name.replace("(1)", "").replace("(2)", "").strip()
            
            logger.info(f"👤 Topper: {topper_name}")
            
            # Process PDF with vision (first 5 pages for quick demo)
            processor = VisionPDFProcessor()
            result = await self.process_pdf_limited_pages(processor, pdf_path, 5)
            
            if not result:
                logger.error(f"❌ Failed to extract content from {pdf_filename}")
                return False
            
            questions = result.get('questions', [])
            logger.info(f"📊 Extracted {len(questions)} questions from {pdf_filename}")
            
            # Store each question in Zilliz
            stored_count = 0
            for i, qa in enumerate(questions, 1):
                try:
                    await self.vector_service.store_topper_content(
                        topper_name=topper_name,
                        institute="VisionIAS",
                        exam_year="2024",
                        question_text=qa.get('question_text', f'Question {i} content'),
                        answer_text=qa.get('student_answer', ''),
                        subject=qa.get('subject', 'General Studies'),
                        marks=qa.get('marks', 10),
                        question_number=f"Q{i}",
                        metadata={
                            'source_file': pdf_filename,
                            'processing_method': 'vision_extraction_zilliz',
                            'page_reference': qa.get('page_reference', f'Page {i}'),
                            'zilliz_storage': True
                        }
                    )
                    stored_count += 1
                    logger.info(f"✅ Stored Q{i} in Zilliz Cloud")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to store Q{i} in Zilliz: {e}")
            
            logger.info(f"🎉 Successfully stored {stored_count}/{len(questions)} questions in Zilliz Cloud")
            return stored_count > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to process {pdf_filename}: {e}")
            return False
    
    async def process_pdf_limited_pages(self, processor, file_path: str, max_pages: int = 5):
        """Process PDF with limited pages for quick results"""
        
        import fitz  # PyMuPDF
        
        logger.info(f"📄 Processing first {max_pages} pages of {os.path.basename(file_path)}")
        
        # Open PDF and check page count
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pages_to_process = min(max_pages, total_pages)
        
        logger.info(f"📊 PDF has {total_pages} pages, processing first {pages_to_process}")
        
        # Process limited pages
        page_analyses = []
        questions_found = 0
        
        for page_num in range(pages_to_process):
            try:
                page = doc[page_num]
                logger.info(f"🔍 Analyzing page {page_num + 1}/{pages_to_process}")
                
                # Convert page to image
                page_image = processor.convert_page_to_image(page)
                
                if page_image:
                    # Analyze with vision
                    analysis = await processor.analyze_page_with_vision(page_image, page_num + 1)
                    page_analyses.append(analysis)
                    
                    # Count questions found
                    page_questions = len(analysis.get("questions_found", []))
                    questions_found += page_questions
                    
                    if page_questions > 0:
                        logger.info(f"✅ Page {page_num + 1}: Found {page_questions} questions")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error processing page {page_num + 1}: {e}")
                continue
        
        doc.close()
        
        # Match questions to answers from limited pages
        matched_qa = processor.match_questions_to_answers(page_analyses)
        total_questions = len(matched_qa)
        total_marks = sum(qa.get("marks", 0) or 0 for qa in matched_qa)
        
        logger.info(f"📊 Processing complete: {total_questions} questions, {total_marks} marks")
        
        return {
            "pdf_filename": os.path.basename(file_path),
            "total_pages": total_pages,
            "pages_processed": pages_to_process,
            "total_questions": total_questions,
            "total_marks": total_marks,
            "questions": matched_qa,
            "processing_method": f"Zilliz storage (first {pages_to_process} pages)",
            "questions_found": questions_found
        }
    
    async def verify_zilliz_data(self):
        """Verify data was stored in Zilliz by performing a search"""
        try:
            logger.info("🔍 Verifying data in Zilliz Cloud...")
            
            # Test search
            results = await self.vector_service.search_similar_topper_answers(
                query_question="What are the main challenges in governance?",
                student_answer="Technology and administration",
                limit=3
            )
            
            if results:
                logger.info(f"✅ Found {len(results)} results in Zilliz Cloud:")
                for i, result in enumerate(results, 1):
                    logger.info(f"   {i}. {result['topper_name']} - {result['subject']}")
                    logger.info(f"      Similarity: {result['similarity_score']:.3f}")
            else:
                logger.warning("⚠️ No results found in search test")
            
            return len(results) > 0
            
        except Exception as e:
            logger.error(f"❌ Failed to verify Zilliz data: {e}")
            return False

async def main():
    """Main execution function"""
    
    print("🚀 Single PDF to Zilliz Cloud Processor")
    print("=" * 50)
    print("📊 Processing one topper PDF and storing in Zilliz Cloud")
    print("🎯 Goal: Verify data appears in your Zilliz dashboard")
    print("=" * 50)
    
    processor = ZillizTopperProcessor()
    
    # Initialize Zilliz service
    if not await processor.initialize_zilliz_service():
        print("❌ Failed to initialize Zilliz Cloud service")
        return
    
    # List available PDFs
    pdf_files = list(Path(processor.toppers_directory).glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in toppers directory")
        return
    
    # Process the first PDF found
    first_pdf = pdf_files[0].name
    print(f"📄 Processing: {first_pdf}")
    
    success = await processor.process_single_pdf_to_zilliz(first_pdf)
    
    if success:
        print(f"✅ Successfully processed {first_pdf} to Zilliz Cloud")
        
        # Verify the data
        verification_success = await processor.verify_zilliz_data()
        
        if verification_success:
            print("🎉 VERIFICATION SUCCESSFUL!")
            print("   ✅ Data is now stored in Zilliz Cloud")
            print("   ✅ You should see it in your Zilliz dashboard")
            print("   🔍 Similarity search is working")
        else:
            print("⚠️ Data stored but verification search failed")
    else:
        print(f"❌ Failed to process {first_pdf}")

if __name__ == "__main__":
    asyncio.run(main())
