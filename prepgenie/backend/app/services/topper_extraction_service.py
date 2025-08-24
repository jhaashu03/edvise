"""
Topper Extraction Service
Processes topper PDFs to extract text content safely before embedding generation
"""
import os
import re
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import fitz  # PyMuPDF
from datetime import datetime
import uuid

from app.models.topper_data import (
    TopperDocument, TopperInfo, TopperPageContent, TopperQuestionAnswer,
    TopperPageType, TopperExtractionBatch, TopperEmbeddingEntry
)
from app.utils.vision_pdf_processor import VisionPDFProcessor

logger = logging.getLogger(__name__)

class TopperExtractionService:
    """Service for extracting content from topper PDFs"""
    
    def __init__(self, output_dir: str = "extracted_topper_data"):
        """Initialize the extraction service"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize vision processor for OCR
        self.vision_processor = VisionPDFProcessor()
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_successful": 0,
            "total_failed": 0,
            "total_pages": 0,
            "total_qa_pairs": 0
        }
        
    def parse_filename(self, filename: str, year_folder: str) -> TopperInfo:
        """
        Parse topper information from filename
        Format: "VisionIAS Toppers Answer Booklet Abhinav Siwach.pdf"
        """
        # Remove .pdf extension
        name = filename.replace('.pdf', '')
        
        # Split by spaces to extract components
        parts = name.split()
        
        # Find institute (usually first word before "Toppers")
        institute = "VisionIAS"  # Default
        for i, part in enumerate(parts):
            if part.lower() == "toppers":
                if i > 0:
                    institute = " ".join(parts[:i])
                break
        
        # Extract topper name (everything after "Booklet")
        topper_name = "Unknown"
        booklet_index = -1
        for i, part in enumerate(parts):
            if part.lower() == "booklet":
                booklet_index = i
                break
        
        if booklet_index >= 0 and booklet_index + 1 < len(parts):
            # Get remaining parts as name, excluding numbers in parentheses
            name_parts = []
            for part in parts[booklet_index + 1:]:
                # Skip parts with parentheses (like "(1)", "(2)")
                if not re.match(r'.*\\(\\d+\\).*', part):
                    name_parts.append(part)
            topper_name = " ".join(name_parts)
        
        return TopperInfo(
            institute=institute,
            topper_name=topper_name,
            exam_year=int(year_folder)
        )
        
    def classify_page_type(self, page_num: int, raw_text: str, vision_analysis: Dict[str, Any]) -> TopperPageType:
        """
        Classify page type based on content and position
        """
        text_lower = raw_text.lower()
        
        # First two pages are usually general info
        if page_num <= 2:
            if any(keyword in text_lower for keyword in ['instructions', 'guidelines', 'rules']):
                return TopperPageType.INSTRUCTIONS
            elif any(keyword in text_lower for keyword in ['candidate', 'roll', 'name']):
                return TopperPageType.CANDIDATE_INFO
            else:
                return TopperPageType.GENERAL_INFO
        
        # From page 3 onwards, look for Q&A content
        if page_num >= 3:
            # Check if page contains questions (Q1, Q2, etc. or numbered questions)
            if re.search(r'\\b[Qq]\\s*\\d+|\\d+\\s*\\.', raw_text):
                return TopperPageType.QUESTION_ANSWER
            # Check if page contains substantial text (likely answers)
            elif len(raw_text.strip()) > 100:
                return TopperPageType.QUESTION_ANSWER
        
        return TopperPageType.OTHER
        
    async def extract_single_pdf(self, file_path: str, topper_info: TopperInfo) -> TopperDocument:
        """Extract content from a single topper PDF"""
        logger.info(f"🔍 Processing: {Path(file_path).name} - {topper_info.topper_name}")
        
        document_id = str(uuid.uuid4())
        
        # Initialize document
        document = TopperDocument(
            document_id=document_id,
            file_path=file_path,
            filename=Path(file_path).name,
            topper_info=topper_info,
            total_pages=0,
            file_size_mb=0.0
        )
        
        try:
            # Get file info
            file_stat = os.stat(file_path)
            document.file_size_mb = file_stat.st_size / (1024 * 1024)
            
            # Open PDF
            doc = fitz.open(file_path)
            document.total_pages = len(doc)
            
            logger.info(f"📄 Processing {document.total_pages} pages for {topper_info.topper_name}")
            
            # Process each page
            for page_num in range(document.total_pages):
                try:
                    current_page = page_num + 1
                    page = doc[page_num]
                    
                    # Convert to image for vision analysis
                    page_image = self.vision_processor.convert_page_to_image(page)
                    
                    if page_image:
                        # Analyze with vision LLM
                        vision_analysis = await self.vision_processor.analyze_page_with_vision(
                            page_image, current_page
                        )
                        
                        # Extract raw text
                        raw_text = vision_analysis.get('extracted_text', '')
                        
                        # Classify page type
                        page_type = self.classify_page_type(current_page, raw_text, vision_analysis)
                        
                        # Create page content
                        page_content = TopperPageContent(
                            page_number=current_page,
                            page_type=page_type,
                            raw_text=raw_text,
                            vision_analysis=vision_analysis,
                            questions_found=vision_analysis.get('questions_found', []),
                            answers_found=vision_analysis.get('answers_found', []),
                            confidence_score=vision_analysis.get('confidence_score', 0.0)
                        )
                        
                        document.pages.append(page_content)
                        
                        logger.info(f"✅ Page {current_page}: {page_type.value}, {len(raw_text)} chars")
                        
                        # Add delay to prevent rate limiting
                        await asyncio.sleep(1.0)
                        
                    else:
                        logger.warning(f"⚠️ Failed to process page {current_page}")
                        
                except Exception as e:
                    logger.error(f"❌ Error processing page {current_page}: {e}")
                    document.error_log.append(f"Page {current_page}: {str(e)}")
            
            doc.close()
            
            # Extract Q&A pairs from processed pages
            self.extract_qa_pairs(document)
            
            # Mark as successful
            document.extraction_successful = True
            
            # Update statistics
            document.processing_stats = {
                "pages_processed": len(document.pages),
                "qa_pairs_found": len(document.question_answers),
                "total_chars": sum(len(p.raw_text) for p in document.pages),
                "avg_confidence": sum(p.confidence_score for p in document.pages) / len(document.pages) if document.pages else 0
            }
            
            logger.info(f"✅ Successfully processed {document.filename}: {len(document.question_answers)} Q&A pairs")
            
        except Exception as e:
            logger.error(f"❌ Failed to process {file_path}: {e}")
            document.error_log.append(f"PDF processing failed: {str(e)}")
            document.extraction_successful = False
            
        return document
    
    def extract_qa_pairs(self, document: TopperDocument):
        """Extract question-answer pairs from processed pages"""
        qa_pairs = []
        current_question = None
        current_answer_parts = []
        
        # Process Q&A pages
        qa_pages = document.get_pages_by_type(TopperPageType.QUESTION_ANSWER)
        
        for page in qa_pages:
            # Look for questions in vision analysis
            for q in page.questions_found:
                # If we were building an answer, save it first
                if current_question and current_answer_parts:
                    self.save_qa_pair(qa_pairs, current_question, current_answer_parts, document.topper_info)
                
                # Start new question
                current_question = q
                current_answer_parts = []
            
            # Look for answers
            for a in page.answers_found:
                if current_question:
                    current_answer_parts.append({
                        'text': a.get('answer_text', ''),
                        'page': page.page_number,
                        'confidence': a.get('confidence', 0.0)
                    })
        
        # Save final Q&A if exists
        if current_question and current_answer_parts:
            self.save_qa_pair(qa_pairs, current_question, current_answer_parts, document.topper_info)
        
        document.question_answers = qa_pairs
        logger.info(f"📝 Extracted {len(qa_pairs)} Q&A pairs from {document.filename}")
    
    def save_qa_pair(self, qa_pairs: List[TopperQuestionAnswer], question: Dict, answer_parts: List[Dict], topper_info: TopperInfo):
        """Save a question-answer pair"""
        # Combine answer parts
        full_answer = " ".join([part['text'] for part in answer_parts])
        page_numbers = [part['page'] for part in answer_parts]
        
        qa_pair = TopperQuestionAnswer(
            question_id=f"{topper_info.topper_name}_{question.get('question_number', len(qa_pairs)+1)}",
            question_number=question.get('question_number', len(qa_pairs)+1),
            question_text=question.get('question_text', ''),
            answer_text=full_answer,
            word_count=len(full_answer.split()),
            page_numbers=page_numbers,
            marks_allocated=question.get('marks', None)
        )
        
        qa_pairs.append(qa_pair)
    
    async def process_directory(self, directory: str) -> List[TopperDocument]:
        """Process all PDF files in a directory"""
        directory_path = Path(directory)
        if not directory_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        year = directory_path.name  # Folder name as year
        pdf_files = list(directory_path.glob("*.pdf"))
        
        logger.info(f"📂 Found {len(pdf_files)} PDF files in {directory}")
        
        documents = []
        for pdf_file in pdf_files:
            try:
                # Parse topper info from filename
                topper_info = self.parse_filename(pdf_file.name, year)
                
                # Extract content
                document = await self.extract_single_pdf(str(pdf_file), topper_info)
                documents.append(document)
                
                # Save individual document
                await self.save_document(document)
                
                # Update global stats
                self.stats["total_processed"] += 1
                if document.extraction_successful:
                    self.stats["total_successful"] += 1
                    self.stats["total_pages"] += document.total_pages
                    self.stats["total_qa_pairs"] += len(document.question_answers)
                else:
                    self.stats["total_failed"] += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing {pdf_file}: {e}")
                self.stats["total_failed"] += 1
        
        return documents
    
    async def process_all_directories(self, base_directories: List[str]) -> TopperExtractionBatch:
        """Process all topper directories"""
        batch_id = str(uuid.uuid4())
        batch = TopperExtractionBatch(
            batch_id=batch_id,
            source_directories=base_directories
        )
        
        logger.info(f"🚀 Starting topper extraction batch {batch_id}")
        
        # Count total files
        for directory in base_directories:
            if os.path.exists(directory):
                pdf_files = list(Path(directory).glob("*.pdf"))
                batch.total_files_found += len(pdf_files)
        
        logger.info(f"📊 Found {batch.total_files_found} total PDF files across all directories")
        
        # Process each directory
        for directory in base_directories:
            if os.path.exists(directory):
                logger.info(f"🔄 Processing directory: {directory}")
                try:
                    documents = await self.process_directory(directory)
                    for doc in documents:
                        batch.add_document(doc)
                except Exception as e:
                    logger.error(f"❌ Error processing directory {directory}: {e}")
            else:
                logger.warning(f"⚠️ Directory not found: {directory}")
        
        # Complete batch
        batch.complete_batch()
        
        # Save batch results
        await self.save_batch(batch)
        
        logger.info(f"🎉 Batch processing completed!")
        logger.info(f"✅ Successful: {batch.successful_extractions}")
        logger.info(f"❌ Failed: {batch.failed_extractions}")
        logger.info(f"📄 Total pages: {batch.total_pages_processed}")
        logger.info(f"📝 Total Q&A pairs: {batch.total_qa_pairs}")
        
        return batch
    
    async def save_document(self, document: TopperDocument):
        """Save individual document to JSON file"""
        filename = f"{document.topper_info.exam_year}_{document.topper_info.topper_name.replace(' ', '_')}_{document.document_id[:8]}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(document.dict(), f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Saved document: {filename}")
    
    async def save_batch(self, batch: TopperExtractionBatch):
        """Save batch results"""
        filename = f"batch_{batch.batch_id}_{batch.processing_started.strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(batch.dict(), f, indent=2, ensure_ascii=False, default=str)
        
        # Also save summary
        summary_filename = f"batch_summary_{batch.processing_started.strftime('%Y%m%d_%H%M%S')}.json"
        summary_filepath = self.output_dir / summary_filename
        
        summary = {
            "batch_id": batch.batch_id,
            "processing_started": batch.processing_started.isoformat(),
            "processing_completed": batch.processing_completed.isoformat() if batch.processing_completed else None,
            "processing_duration_seconds": batch.get_processing_duration(),
            "total_files_found": batch.total_files_found,
            "successful_extractions": batch.successful_extractions,
            "failed_extractions": batch.failed_extractions,
            "total_pages_processed": batch.total_pages_processed,
            "total_qa_pairs": batch.total_qa_pairs,
            "total_word_count": batch.total_word_count,
            "global_stats": self.stats
        }
        
        with open(summary_filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"💾 Saved batch results: {filename}")
        logger.info(f"💾 Saved batch summary: {summary_filename}")

# Global instance
topper_extraction_service = TopperExtractionService()
