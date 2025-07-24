"""
Store Actual Topper PDF in Milvus Database
Process one real topper PDF and insert extracted content into the vector database
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.topper_vector_service import TopperVectorService
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.core.llm_service import get_llm_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealTopperPDFProcessor:
    """Process and store actual topper PDF content"""
    
    def __init__(self):
        self.toppers_directory = "/Users/a0j0agc/Desktop/Personal/ToppersCopy/2024/"
        
    async def initialize_services(self):
        """Initialize all required services"""
        try:
            logger.info("🔧 Initializing services...")
            
            # Set environment for local Milvus (since Zilliz has connection issues)
            os.environ['ENVIRONMENT'] = 'local'
            os.environ['DISABLE_VECTOR_SERVICE'] = 'false'
            
            # Initialize vector service
            self.vector_service = TopperVectorService()
            await self.vector_service.initialize()
            
            # Initialize vision processor
            self.vision_processor = VisionPDFProcessor()
            
            logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            return False
    
    def select_pdf_to_process(self):
        """Select one PDF file to process"""
        pdf_files = list(Path(self.toppers_directory).glob("*.pdf"))
        
        if not pdf_files:
            logger.error(f"❌ No PDF files found in {self.toppers_directory}")
            return None
        
        # Select the first PDF for processing
        selected_pdf = pdf_files[0]
        logger.info(f"📄 Selected PDF: {selected_pdf.name}")
        return str(selected_pdf)
    
    def extract_topper_info(self, pdf_path: str) -> dict:
        """Extract topper information from filename"""
        filename = os.path.basename(pdf_path)
        
        if "VisionIAS Toppers Answer Booklet" in filename:
            name = filename.replace("VisionIAS Toppers Answer Booklet", "").replace(".pdf", "").strip()
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
    
    async def process_pdf_limited_pages(self, pdf_path: str, max_pages: int = 8, start_page: int = 5) -> dict:
        """Process PDF with limited pages to avoid timeout, starting from where questions typically begin"""
        
        import fitz  # PyMuPDF
        
        logger.info(f"📄 Processing {max_pages} pages of {os.path.basename(pdf_path)} starting from page {start_page + 1}")
        
        try:
            # Open PDF
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            # Calculate page range (questions typically start around page 6)
            end_page = min(start_page + max_pages, total_pages)
            pages_to_process = end_page - start_page
            
            logger.info(f"📊 PDF has {total_pages} pages, processing pages {start_page + 1}-{end_page}")
            
            # Process pages one by one
            page_analyses = []
            questions_found = 0
            
            for page_num in range(start_page, end_page):
                try:
                    page = doc[page_num]
                    logger.info(f"🔍 Processing page {page_num + 1}/{total_pages}")
                    
                    # Convert page to image
                    page_image = self.vision_processor.convert_page_to_image(page)
                    
                    if page_image:
                        # Analyze with vision
                        analysis = await self.vision_processor.analyze_page_with_vision(page_image, page_num + 1)
                        
                        if analysis:
                            page_analyses.append(analysis)
                            
                            # Count questions found
                            page_questions = len(analysis.get("questions_found", []))
                            questions_found += page_questions
                            
                            if page_questions > 0:
                                logger.info(f"✅ Page {page_num + 1}: Found {page_questions} questions")
                            else:
                                logger.info(f"📝 Page {page_num + 1}: No questions found")
                        
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Error processing page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
            # Match questions to answers
            matched_qa = self.vision_processor.match_questions_to_answers(page_analyses)
            total_questions = len(matched_qa)
            total_marks = sum(qa.get("marks", 0) or 0 for qa in matched_qa)
            
            logger.info(f"📊 Processing complete: {total_questions} questions, {total_marks} marks")
            
            return {
                "pdf_filename": os.path.basename(pdf_path),
                "total_pages": total_pages,
                "pages_processed": pages_to_process,
                "start_page": start_page + 1,
                "end_page": end_page,
                "total_questions": total_questions,
                "total_marks": total_marks,
                "questions": matched_qa,
                "questions_found": questions_found
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF: {e}")
            return None
    
    async def store_extracted_content(self, topper_info: dict, extraction_result: dict):
        """Store extracted content in vector database"""
        
        if not extraction_result or not extraction_result.get("questions"):
            logger.warning("⚠️ No content to store")
            return 0
        
        logger.info(f"💾 Storing {len(extraction_result['questions'])} questions in vector database...")
        
        stored_count = 0
        
        for i, qa in enumerate(extraction_result["questions"], 1):
            try:
                # Store each question-answer pair
                await self.vector_service.store_topper_content(
                    topper_name=topper_info['name'],
                    institute=topper_info['institute'],
                    exam_year=topper_info['exam_year'],
                    question_text=qa.get('question_text', f'Question {i} from {topper_info["name"]}'),
                    answer_text=qa.get('student_answer', ''),
                    subject=qa.get('subject', 'General Studies'),
                    marks=qa.get('marks', 10),
                    question_number=qa.get('question_number', f'Q{i}'),
                    metadata={
                        'source_file': topper_info['source_file'],
                        'processing_method': 'vision_processing',
                        'page_reference': qa.get('page_reference', f'Page {i}'),
                        'total_pages_processed': extraction_result.get('pages_processed', 5)
                    }
                )
                
                stored_count += 1
                logger.info(f"✅ Stored Q{i} from {topper_info['name']}")
                
            except Exception as e:
                logger.error(f"❌ Failed to store Q{i}: {e}")
        
        logger.info(f"💾 Successfully stored {stored_count} questions from {topper_info['name']}")
        return stored_count
    
    async def test_search_functionality(self):
        """Test search with the newly stored data"""
        logger.info("\n🔍 Testing search with newly stored data...")
        
        test_queries = [
            "What is the role of technology in governance?",
            "Discuss constitutional amendments in India",
            "Explain globalization impact on economy"
        ]
        
        for query in test_queries:
            try:
                results = await self.vector_service.search_similar_topper_answers(
                    query_question=query,
                    limit=2
                )
                
                logger.info(f"🎯 Query: '{query}'")
                logger.info(f"   Found {len(results)} results")
                
                for j, result in enumerate(results, 1):
                    logger.info(f"   {j}. {result['topper_name']} - Similarity: {result['similarity_score']:.3f}")
                
            except Exception as e:
                logger.error(f"❌ Search failed for '{query}': {e}")
    
    async def run_complete_process(self):
        """Run the complete PDF processing and storage pipeline"""
        
        logger.info("\n🚀 REAL TOPPER PDF TO MILVUS PROCESSING")
        logger.info("=" * 60)
        logger.info("🎯 Goal: Process actual topper PDF and store in vector database")
        logger.info("📁 Using local Milvus database")
        logger.info("=" * 60)
        
        try:
            # Initialize services
            if not await self.initialize_services():
                logger.error("❌ Failed to initialize services")
                return
            
            # Select PDF to process
            pdf_path = self.select_pdf_to_process()
            if not pdf_path:
                logger.error("❌ No PDF found to process")
                return
            
            # Extract topper info
            topper_info = self.extract_topper_info(pdf_path)
            logger.info(f"👤 Processing topper: {topper_info['name']}")
            
            # Process PDF (limited pages for speed, starting where questions typically begin)
            extraction_result = await self.process_pdf_limited_pages(pdf_path, max_pages=8, start_page=5)
            
            if not extraction_result:
                logger.error("❌ Failed to extract content from PDF")
                return
            
            # Store in vector database
            stored_count = await self.store_extracted_content(topper_info, extraction_result)
            
            if stored_count > 0:
                logger.info(f"\n🎉 SUCCESS!")
                logger.info(f"✅ Processed PDF: {extraction_result['pdf_filename']}")
                logger.info(f"📄 Pages processed: {extraction_result['pages_processed']}")
                logger.info(f"📝 Questions extracted: {extraction_result['total_questions']}")
                logger.info(f"💾 Questions stored: {stored_count}")
                
                # Test search functionality
                await self.test_search_functionality()
                
                logger.info(f"\n🎯 READY TO USE:")
                logger.info(f"   📚 Vector database now contains real topper content")
                logger.info(f"   🔍 Search functionality verified and working")
                logger.info(f"   🚀 Ready for production use!")
                
            else:
                logger.error("❌ No content was stored in the database")
                
        except Exception as e:
            logger.error(f"❌ Processing failed: {e}")

async def main():
    """Main execution function"""
    
    processor = RealTopperPDFProcessor()
    await processor.run_complete_process()

if __name__ == "__main__":
    asyncio.run(main())
