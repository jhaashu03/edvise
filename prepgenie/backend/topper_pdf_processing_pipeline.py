"""
Comprehensive Topper PDF Processing Pipeline
Processes actual topper PDFs from /Users/a0j0agc/Desktop/Personal/ToppersCopy/2024/
Extracts text, generates embeddings, and stores in Milvus database
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import re

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.llm_service import get_llm_service, LLMService
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.services.topper_vector_service import TopperVectorService
from app.models.topper_reference import TopperReference, TopperAnswer
from app.db.database import SessionLocal, get_db
from sqlalchemy.orm import Session
from sqlalchemy import select

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('topper_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TopperPDFProcessor:
    """Main processor for topper PDF files"""
    
    def __init__(self):
        self.toppers_directory = "/Users/a0j0agc/Desktop/Personal/ToppersCopy/2024/"
        self.llm_service = None
        self.vision_processor = None
        self.vector_service = None
        self.db = None
        self.processed_count = 0
        self.failed_count = 0
        self.extraction_results = []
        
    async def initialize(self):
        """Initialize all required services"""
        logger.info("Initializing Topper PDF Processor...")
        
        try:
            # Initialize services
            self.llm_service = get_llm_service()
            self.vision_processor = VisionPDFProcessor()
            self.vector_service = TopperVectorService()
            self.db = SessionLocal()
            
            # Initialize vector service
            await self.vector_service.initialize()
            
            logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            return False
    
    async def discover_topper_pdfs(self) -> List[str]:
        """Discover all topper PDF files in the directory"""
        logger.info(f"Scanning directory: {self.toppers_directory}")
        
        if not os.path.exists(self.toppers_directory):
            logger.error(f"Directory does not exist: {self.toppers_directory}")
            return []
        
        pdf_files = []
        for file_name in os.listdir(self.toppers_directory):
            if file_name.endswith('.pdf') and not file_name.startswith('.'):
                full_path = os.path.join(self.toppers_directory, file_name)
                pdf_files.append(full_path)
        
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        return sorted(pdf_files)
    
    def extract_topper_info_from_filename(self, file_path: str) -> Dict[str, str]:
        """Extract topper name and other info from filename"""
        filename = os.path.basename(file_path)
        
        # Pattern: VisionIAS Toppers Answer Booklet [Name] (optional number).pdf
        pattern = r'VisionIAS Toppers Answer Booklet ([^(]+?)(?:\s*\(\d+\))?.pdf'
        match = re.search(pattern, filename, re.IGNORECASE)
        
        if match:
            name = match.group(1).strip()
            return {
                'name': name,
                'institute': 'VisionIAS',
                'exam_year': '2024',
                'source_file': filename
            }
        else:
            # Fallback extraction
            name = filename.replace('VisionIAS Toppers Answer Booklet', '').replace('.pdf', '').strip()
            return {
                'name': name,
                'institute': 'VisionIAS', 
                'exam_year': '2024',
                'source_file': filename
            }
    
    async def extract_pdf_content(self, file_path: str) -> Optional[Dict]:
        """Extract content from a single PDF using Vision processor"""
        logger.info(f"Processing PDF: {os.path.basename(file_path)}")
        
        try:
            # Extract topper info from filename
            topper_info = self.extract_topper_info_from_filename(file_path)
            logger.info(f"Extracted info: {topper_info}")
            
            # Use Vision PDF processor to extract content
            extraction_result = await self.vision_processor.process_pdf_with_vision(
                file_path=file_path,
                progress_callback=None
            )
            
            if not extraction_result:
                logger.error(f"Vision processing failed for {topper_info['name']}: No result returned")
                return None
            
            # Check if we got meaningful results
            if extraction_result.get('total_questions', 0) == 0:
                logger.warning(f"No questions found for {topper_info['name']}: {extraction_result.get('pdf_filename')}")
                # Don't return None, continue processing as it might still have some content
            
            # Structure the content with LLM (use the questions data instead of raw text)
            questions_data = extraction_result.get('questions', [])
            if questions_data:
                structured_content = await self.structure_topper_content_from_questions(
                    questions_data,
                    topper_info
                )
            else:
                logger.warning(f"No questions data found for {topper_info['name']}")
                structured_content = {
                    "topper_name": topper_info['name'],
                    "questions_answers": [],
                    "extraction_metadata": {
                        "total_questions_found": 0,
                        "content_quality": "low",
                        "processing_notes": "No questions extracted"
                    }
                }
            
            return {
                'topper_info': topper_info,
                'raw_extraction': extraction_result,
                'structured_content': structured_content,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None
    
    async def structure_topper_content_from_questions(self, questions_data: List[Dict], topper_info: Dict) -> Dict:
        """Structure already extracted questions data into our topper format"""
        logger.info(f"Structuring {len(questions_data)} questions for {topper_info['name']}...")
        
        structured_questions = []
        
        for qa in questions_data:
            # Convert from vision processor format to topper format
            structured_qa = {
                "question_number": qa.get("question_number", "Q?"),
                "question_text": qa.get("question_text", ""),
                "answer_text": qa.get("student_answer", ""),
                "subject": self.identify_subject_from_content(qa.get("question_text", "")),
                "estimated_marks": qa.get("marks", 10),
                "word_limit": qa.get("word_limit", 150),
                "page_reference": self._get_page_reference(qa),
                "handwriting_quality": qa.get("handwriting_quality", "moderate"),
                "visual_elements": qa.get("visual_elements", [])
            }
            structured_questions.append(structured_qa)
        
        return {
            "topper_name": topper_info['name'],
            "institute": topper_info['institute'],
            "exam_year": topper_info['exam_year'],
            "questions_answers": structured_questions,
            "extraction_metadata": {
                "total_questions_found": len(questions_data),
                "content_quality": "high" if len(questions_data) > 5 else "medium" if len(questions_data) > 0 else "low",
                "processing_notes": f"Successfully extracted {len(questions_data)} questions using vision processing"
            }
        }
    
    def _get_page_reference(self, qa: Dict) -> str:
        """Extract page reference from question data"""
        source_pages = qa.get("source_pages", {})
        if isinstance(source_pages, dict):
            q_page = source_pages.get("question", 1)
            a_pages = source_pages.get("answers", [1])
            if isinstance(a_pages, list) and len(a_pages) > 1:
                return f"Q: Page {q_page}, A: Pages {a_pages[0]}-{a_pages[-1]}"
            else:
                return f"Q: Page {q_page}, A: Page {a_pages[0] if a_pages else q_page}"
        else:
            return f"Page {qa.get('source_page', 1)}"
    
    def identify_subject_from_content(self, question_text: str) -> str:
        """Identify subject area from question content"""
        text = question_text.lower()
        
        # GS-I indicators
        if any(word in text for word in ['history', 'culture', 'heritage', 'ancient', 'medieval', 'modern india', 'freedom', 'art', 'dance', 'literature']):
            return "GS-I"
        
        # GS-II indicators  
        elif any(word in text for word in ['governance', 'constitution', 'parliament', 'judiciary', 'international', 'bilateral', 'foreign policy', 'polity']):
            return "GS-II"
            
        # GS-III indicators
        elif any(word in text for word in ['economy', 'economic', 'technology', 'innovation', 'agriculture', 'industry', 'infrastructure', 'environment', 'climate']):
            return "GS-III"
            
        # GS-IV indicators
        elif any(word in text for word in ['ethics', 'integrity', 'aptitude', 'moral', 'values', 'attitude', 'emotional intelligence']):
            return "GS-IV"
        
        else:
            return "GS-General"
    
    def _create_fallback_structure(self, questions_data: List[Dict], topper_info: Dict) -> Dict:
        """Create a fallback structure when LLM processing fails"""
        return {
            "topper_name": topper_info['name'],
            "institute": topper_info['institute'],
            "exam_year": "2024",
            "questions_answers": [
                {
                    "question_number": "Q1",
                    "question_text": "Content extraction incomplete - manual review needed",
                    "answer_text": "No structured content available",  # Fallback text
                    "subject": "GS-II",
                    "estimated_marks": 15,
                    "page_reference": "Full document"
                }
            ],
            "extraction_metadata": {
                "total_questions_found": 1,
                "content_quality": "low",
                "processing_notes": "Fallback structure - LLM processing failed"
            }
        }
    
    async def store_in_database(self, processed_content: Dict) -> bool:
        """Store processed content in PostgreSQL database"""
        try:
            topper_info = processed_content['topper_info']
            structured_content = processed_content['structured_content']
            
            # Check if topper already exists
            existing_topper = self.db.execute(
                select(TopperReference).where(
                    TopperReference.name == topper_info['name'],
                    TopperReference.exam_year == 2024
                )
            ).scalar_one_or_none()
            
            if existing_topper:
                logger.info(f"Topper {topper_info['name']} already exists in database")
                topper_ref = existing_topper
            else:
                # Create new topper reference
                topper_ref = TopperReference(
                    name=topper_info['name'],
                    rank=None,  # We don't have rank info from filename
                    exam_year=2024,
                    institute=topper_info['institute'],
                    source_file=topper_info['source_file'],
                    total_questions=structured_content['extraction_metadata']['total_questions_found'],
                    extraction_metadata=structured_content['extraction_metadata']
                )
                self.db.add(topper_ref)
                self.db.flush()  # Get the ID
                logger.info(f"Created new topper reference for {topper_info['name']}")
            
            # Store individual answers
            answers_stored = 0
            for qa in structured_content.get('questions_answers', []):
                topper_answer = TopperAnswer(
                    topper_reference_id=topper_ref.id,
                    question_number=qa['question_number'],
                    question_text=qa['question_text'],
                    answer_text=qa['answer_text'],
                    subject=qa['subject'],
                    marks=qa['estimated_marks'],
                    page_reference=qa.get('page_reference', '')
                )
                self.db.add(topper_answer)
                answers_stored += 1
            
            self.db.commit()
            logger.info(f"Stored {answers_stored} answers for {topper_info['name']}")
            
            # Store the topper reference ID for vector processing
            processed_content['topper_reference_id'] = topper_ref.id
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database storage failed: {e}")
            return False
    
    async def generate_and_store_embeddings(self, processed_content: Dict) -> bool:
        """Generate embeddings and store in Milvus"""
        try:
            structured_content = processed_content['structured_content']
            topper_ref_id = processed_content['topper_reference_id']
            
            embeddings_data = []
            
            for qa in structured_content.get('questions_answers', []):
                # Combine question and answer for embedding
                combined_text = f"Question: {qa['question_text']}\nAnswer: {qa['answer_text']}"
                
                embedding_data = {
                    'topper_reference_id': topper_ref_id,
                    'topper_name': structured_content['topper_name'],
                    'question_number': qa['question_number'],
                    'question_text': qa['question_text'],
                    'answer_text': qa['answer_text'],
                    'subject': qa['subject'],
                    'marks': qa['estimated_marks'],
                    'exam_year': 2024,
                    'institute': structured_content['institute'],
                    'combined_text': combined_text
                }
                embeddings_data.append(embedding_data)
            
            # Bulk insert into Milvus
            success = await self.vector_service.bulk_insert_toppers(embeddings_data)
            
            if success:
                logger.info(f"✅ Generated and stored {len(embeddings_data)} embeddings for {structured_content['topper_name']}")
                return True
            else:
                logger.error(f"❌ Failed to store embeddings for {structured_content['topper_name']}")
                return False
                
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return False
    
    async def process_single_pdf(self, file_path: str) -> bool:
        """Process a single PDF file completely"""
        try:
            logger.info(f"\n🔄 Processing: {os.path.basename(file_path)}")
            
            # Step 1: Extract content
            processed_content = await self.extract_pdf_content(file_path)
            if not processed_content:
                logger.error(f"❌ Content extraction failed for {file_path}")
                return False
            
            # Step 2: Store in database
            db_success = await self.store_in_database(processed_content)
            if not db_success:
                logger.error(f"❌ Database storage failed for {file_path}")
                return False
            
            # Step 3: Generate and store embeddings
            vector_success = await self.generate_and_store_embeddings(processed_content)
            if not vector_success:
                logger.error(f"❌ Vector storage failed for {file_path}")
                return False
            
            # Store results for reporting
            self.extraction_results.append({
                'file': os.path.basename(file_path),
                'topper_name': processed_content['topper_info']['name'],
                'questions_extracted': len(processed_content['structured_content'].get('questions_answers', [])),
                'status': 'SUCCESS',
                'processing_time': datetime.now().isoformat()
            })
            
            logger.info(f"✅ Successfully processed {processed_content['topper_info']['name']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to process {file_path}: {e}")
            self.extraction_results.append({
                'file': os.path.basename(file_path),
                'status': 'FAILED',
                'error': str(e),
                'processing_time': datetime.now().isoformat()
            })
            return False
    
    async def process_all_toppers(self):
        """Process all topper PDFs in the directory"""
        logger.info("\n🚀 Starting Topper PDF Processing Pipeline")
        logger.info("=" * 60)
        
        # Initialize services
        if not await self.initialize():
            logger.error("❌ Failed to initialize - stopping pipeline")
            return
        
        # Discover PDFs
        pdf_files = await self.discover_topper_pdfs()
        if not pdf_files:
            logger.error("❌ No PDF files found - stopping pipeline")
            return
        
        logger.info(f"📚 Found {len(pdf_files)} topper PDFs to process")
        
        # Process each PDF
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n📖 Processing {i}/{len(pdf_files)}: {os.path.basename(pdf_file)}")
            
            success = await self.process_single_pdf(pdf_file)
            
            if success:
                self.processed_count += 1
            else:
                self.failed_count += 1
            
            # Progress update
            logger.info(f"Progress: {self.processed_count} successful, {self.failed_count} failed")
        
        # Final report
        await self.generate_final_report()
    
    async def generate_final_report(self):
        """Generate processing summary report"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 TOPPER PROCESSING PIPELINE COMPLETE")
        logger.info("=" * 60)
        
        logger.info(f"✅ Successfully processed: {self.processed_count}")
        logger.info(f"❌ Failed to process: {self.failed_count}")
        logger.info(f"📁 Total files processed: {len(self.extraction_results)}")
        
        # Save detailed results
        report_file = f"topper_processing_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'processing_summary': {
                    'total_files': len(self.extraction_results),
                    'successful': self.processed_count,
                    'failed': self.failed_count,
                    'processing_date': datetime.now().isoformat()
                },
                'detailed_results': self.extraction_results
            }, f, indent=2)
        
        logger.info(f"📋 Detailed report saved: {report_file}")
        
        # Vector database stats
        try:
            stats = await self.vector_service.get_collection_stats()
            logger.info(f"🔢 Vector database stats: {stats}")
        except Exception as e:
            logger.error(f"Could not get vector stats: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db:
            self.db.close()
        logger.info("🧹 Cleanup complete")

# Command line interface
async def main():
    """Main execution function"""
    processor = TopperPDFProcessor()
    
    try:
        await processor.process_all_toppers()
    except KeyboardInterrupt:
        logger.info("\n⏹️ Processing interrupted by user")
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
    finally:
        await processor.cleanup()

if __name__ == "__main__":
    print("🎯 Topper PDF Processing Pipeline")
    print("Processing VisionIAS 2024 Topper Answer Booklets")
    print("-" * 50)
    
    # Run the pipeline
    asyncio.run(main())
