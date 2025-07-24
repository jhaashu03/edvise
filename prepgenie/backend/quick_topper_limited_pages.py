"""
Quick Topper Processing - Limited Pages Version
Process only the first few pages of each topper PDF to get meaningful results quickly
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.core.llm_service import get_llm_service
from app.services.topper_vector_service import TopperVectorService
from app.db.database import SessionLocal

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class QuickTopperProcessor:
    """Process toppers quickly by limiting pages processed"""
    
    def __init__(self):
        self.toppers_directory = "/Users/a0j0agc/Desktop/Personal/ToppersCopy/2024/"
        self.max_pages_per_pdf = 10  # Only process first 10 pages
        self.processed_count = 0
        
    async def initialize(self):
        """Initialize services"""
        try:
            logger.info("🔧 Initializing Quick Topper Processor...")
            
            # Initialize vector service (local mode for now)
            os.environ['ENVIRONMENT'] = 'local'
            os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
            
            self.vector_service = TopperVectorService()
            await self.vector_service.initialize()
            
            logger.info("✅ Quick processor initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False
    
    def extract_topper_info_from_filename(self, file_path: str) -> dict:
        """Extract topper name from filename"""
        filename = os.path.basename(file_path)
        
        # Parse VisionIAS format: "VisionIAS Toppers Answer Booklet Name.pdf"
        if "VisionIAS Toppers Answer Booklet" in filename:
            name = filename.replace("VisionIAS Toppers Answer Booklet", "").replace(".pdf", "").strip()
            # Clean up name
            name = name.replace("(1)", "").replace("(2)", "").strip()
            return {
                'name': name,
                'institute': 'VisionIAS',
                'exam_year': '2024',
                'source_file': filename
            }
        else:
            name = filename.replace('.pdf', '').strip()
            return {
                'name': name,
                'institute': 'VisionIAS', 
                'exam_year': '2024',
                'source_file': filename
            }
    
    async def process_single_topper_quick(self, file_path: str) -> dict:
        """Process a single topper PDF (first few pages only)"""
        
        topper_info = self.extract_topper_info_from_filename(file_path)
        logger.info(f"🎯 Quick processing: {topper_info['name']} (max {self.max_pages_per_pdf} pages)")
        
        try:
            # Create a modified vision processor that stops after N pages
            processor = VisionPDFProcessor()
            
            # Process PDF but limit pages
            result = await self.process_pdf_limited_pages(processor, file_path, self.max_pages_per_pdf)
            
            if result:
                logger.info(f"✅ Quick processed {topper_info['name']}: {result.get('total_questions', 0)} questions found")
                
                # Store in vector database if we found content
                questions = result.get('questions', [])
                if questions:
                    await self.store_topper_content_in_vector_db(topper_info, questions)
                
                self.processed_count += 1
                return {
                    'topper_info': topper_info,
                    'extraction_result': result,
                    'success': True
                }
            else:
                logger.warning(f"⚠️ No content extracted for {topper_info['name']}")
                return {
                    'topper_info': topper_info,
                    'extraction_result': None,
                    'success': False
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to process {topper_info['name']}: {e}")
            return {
                'topper_info': topper_info,
                'extraction_result': None,
                'success': False,
                'error': str(e)
            }
    
    async def process_pdf_limited_pages(self, processor, file_path: str, max_pages: int) -> dict:
        """Process PDF with page limit using a modified approach"""
        
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
        
        logger.info(f"📊 Quick processing complete: {total_questions} questions, {total_marks} marks")
        
        # Return simplified result
        return {
            "pdf_filename": os.path.basename(file_path),
            "total_pages": total_pages,
            "pages_processed": pages_to_process,
            "total_questions": total_questions,
            "total_marks": total_marks,
            "questions": matched_qa,
            "processing_method": f"Quick processing (first {pages_to_process} pages)",
            "questions_found": questions_found
        }
    
    async def store_topper_content_in_vector_db(self, topper_info: dict, questions: list):
        """Store topper content in vector database"""
        
        try:
            logger.info(f"💾 Storing {len(questions)} questions in vector database...")
            
            for qa in questions:
                # Create embedding for the question-answer pair
                content_text = f"Question: {qa.get('question_text', '')} Answer: {qa.get('student_answer', '')}"
                
                # Store in vector database
                await self.vector_service.store_topper_content(
                    topper_name=topper_info['name'],
                    institute=topper_info['institute'],
                    exam_year=topper_info['exam_year'],
                    question_text=qa.get('question_text', ''),
                    answer_text=qa.get('student_answer', ''),
                    subject=qa.get('subject', 'General Studies'),
                    marks=qa.get('marks', 10),
                    question_number=qa.get('question_number', 'Q1'),
                    metadata={
                        'source_file': topper_info['source_file'],
                        'processing_method': 'quick_processing',
                        'page_reference': qa.get('page_reference', 'Page 1-10')
                    }
                )
            
            logger.info(f"✅ Stored {len(questions)} questions in vector database")
            
        except Exception as e:
            logger.error(f"❌ Failed to store in vector database: {e}")
    
    async def process_all_toppers_quick(self):
        """Process all topper PDFs quickly"""
        
        # Find all PDF files
        pdf_files = list(Path(self.toppers_directory).glob("*.pdf"))
        logger.info(f"📁 Found {len(pdf_files)} topper PDFs to process quickly")
        
        results = []
        success_count = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n🚀 Processing {i}/{len(pdf_files)}: {pdf_file.name}")
            
            result = await self.process_single_topper_quick(str(pdf_file))
            results.append(result)
            
            if result['success']:
                success_count += 1
            
            # Progress update
            logger.info(f"📊 Progress: {i}/{len(pdf_files)} processed, {success_count} successful")
        
        # Final summary
        logger.info(f"\n🎉 QUICK PROCESSING COMPLETE!")
        logger.info(f"✅ Successfully processed: {success_count}/{len(pdf_files)} toppers")
        logger.info(f"📊 Total questions extracted: {sum(r.get('extraction_result', {}).get('total_questions', 0) for r in results if r['success'])}")
        
        return results

async def main():
    """Main execution function"""
    
    print("🚀 Quick Topper Processing (Limited Pages)")
    print("=" * 50)
    print("⚡ Processing only first 10 pages per PDF for speed")
    print("🎯 Goal: Get meaningful results quickly for testing")
    print("=" * 50)
    
    processor = QuickTopperProcessor()
    
    # Initialize
    if not await processor.initialize():
        print("❌ Failed to initialize processor")
        return
    
    # Process all toppers quickly
    results = await processor.process_all_toppers_quick()
    
    print("\n🎯 READY FOR FULL PIPELINE:")
    print("   ✅ Vector database populated with sample content")
    print("   🔍 Can test similarity search functionality")
    print("   🚀 Can expand to full pages when needed")

if __name__ == "__main__":
    asyncio.run(main())
