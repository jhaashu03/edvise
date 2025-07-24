#!/usr/bin/env python3
"""
Enhanced Topper Content Extractor with Vector Database Support
Extracts content from multiple topper PDFs and stores in both PostgreSQL and Milvus
Handles 100-200+ topper copies efficiently with batch processing
"""

import sys
import os
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add the backend directory to Python path
sys.path.append('/Users/a0j0agc/Desktop/Personal/edvise/prepgenie/backend')

from app.db.database import SessionLocal
from app.models.topper_reference import TopperReference, TopperPattern
from app.services.topper_vector_service import topper_vector_service
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.core.llm_service import get_llm_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('topper_extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EnhancedTopperExtractor:
    """Enhanced extractor with vector database integration"""
    
    def __init__(self):
        self.pdf_processor = VisionPDFProcessor()
        self.llm_service = get_llm_service()
        self.upload_dir = Path("/Users/a0j0agc/Desktop/Personal/edvise/uploads")
        self.processed_count = 0
        self.failed_count = 0
        
    async def initialize_services(self):
        """Initialize all services"""
        try:
            # Connect to vector database
            await topper_vector_service.connect()
            logger.info("✅ Connected to vector database")
            
            # Get collection stats
            stats = await topper_vector_service.get_collection_stats()
            logger.info(f"📊 Current database stats: {stats}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            raise
    
    async def extract_from_single_pdf(self, pdf_path: Path, topper_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract content from a single topper PDF"""
        try:
            logger.info(f"🔍 Processing: {pdf_path.name}")
            
            # Extract content using vision processor
            extracted_content = await self.pdf_processor.extract_full_content(str(pdf_path))
            
            if not extracted_content or 'pages' not in extracted_content:
                logger.warning(f"⚠️  No content extracted from {pdf_path.name}")
                return []
            
            # Process pages to identify questions and answers
            questions_answers = await self._identify_questions_and_answers(
                extracted_content['pages'], 
                topper_info
            )
            
            logger.info(f"✅ Extracted {len(questions_answers)} Q&A pairs from {pdf_path.name}")
            return questions_answers
            
        except Exception as e:
            logger.error(f"❌ Failed to process {pdf_path.name}: {e}")
            return []
    
    async def _identify_questions_and_answers(self, pages: List[Dict], topper_info: Dict) -> List[Dict[str, Any]]:
        """Use LLM to identify and structure questions and answers"""
        
        # Combine all page text
        full_text = ""
        for page in pages:
            if 'text' in page:
                full_text += f"\n--- Page {page.get('page_number', 0)} ---\n{page['text']}\n"
        
        if not full_text.strip():
            return []
        
        # Use LLM to structure the content
        structuring_prompt = f"""
You are analyzing a topper's answer booklet. Extract individual questions and answers from this content.

TOPPER INFORMATION:
- Name: {topper_info.get('name', 'Unknown')}
- Institute: {topper_info.get('institute', 'Unknown')}
- Rank: {topper_info.get('rank', 'Unknown')}
- Year: {topper_info.get('year', 2024)}

CONTENT TO ANALYZE:
{full_text[:8000]}  # Limit to avoid token limits

TASK: Identify individual questions and their corresponding answers. For each Q&A pair, provide:

1. Question identification (look for "Q.", "Question", numbered questions)
2. Answer text (everything between current question and next question)
3. Subject inference (based on content - History, Geography, Polity, etc.)
4. Estimated marks (based on answer length and complexity)

Return results in JSON format:
{{
    "questions_answers": [
        {{
            "question_id": "Q1",
            "question_text": "Exact question text...",
            "answer_text": "Complete answer text...",
            "subject": "History/Geography/Polity/etc",
            "topic": "Specific topic if identifiable",
            "estimated_marks": 10,
            "word_count": 250,
            "page_references": [1, 2]
        }}
    ]
}}

Focus on complete, well-formed questions and answers. Skip fragments or incomplete content.
"""
        
        try:
            response = await self.llm_service.simple_chat(
                user_message=structuring_prompt,
                temperature=0.2
            )
            
            # Parse response
            import json
            try:
                structured_data = json.loads(response)
                qa_pairs = structured_data.get('questions_answers', [])
                
                # Enhance each Q&A with topper metadata
                for qa in qa_pairs:
                    qa.update({
                        'topper_name': topper_info.get('name', 'Unknown'),
                        'institute': topper_info.get('institute'),
                        'rank': topper_info.get('rank'),
                        'exam_year': topper_info.get('year'),
                        'source_document': topper_info.get('filename'),
                        'extraction_timestamp': datetime.now().isoformat()
                    })
                
                return qa_pairs
                
            except json.JSONDecodeError:
                logger.warning("Failed to parse LLM JSON response, attempting text extraction")
                return await self._fallback_text_extraction(full_text, topper_info)
                
        except Exception as e:
            logger.error(f"LLM structuring failed: {e}")
            return await self._fallback_text_extraction(full_text, topper_info)
    
    async def _fallback_text_extraction(self, text: str, topper_info: Dict) -> List[Dict[str, Any]]:
        """Fallback extraction using text patterns"""
        import re
        
        qa_pairs = []
        
        # Simple pattern matching for questions
        question_patterns = [
            r'Q\.?\s*\d+\.?\s*(.*?)(?=Q\.?\s*\d+|$)',
            r'Question\s*\d+\.?\s*(.*?)(?=Question\s*\d+|$)',
            r'\d+\.?\s*(.*?)(?=\d+\.|$)'
        ]
        
        for pattern in question_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches and len(matches) > 1:  # At least 2 questions found
                for i, match in enumerate(matches[:10]):  # Limit to first 10
                    if len(match.strip()) > 50:  # Reasonable content length
                        # Try to split question and answer
                        parts = match.split('\n', 1)
                        if len(parts) >= 2:
                            question_text = parts[0].strip()[:500]
                            answer_text = parts[1].strip()[:2000] 
                            
                            qa_pairs.append({
                                'question_id': f"Q{i+1}",
                                'question_text': question_text,
                                'answer_text': answer_text,
                                'subject': 'General Studies',  # Default
                                'topic': 'Various',
                                'estimated_marks': 10,
                                'word_count': len(answer_text.split()),
                                'page_references': [1],
                                'topper_name': topper_info.get('name', 'Unknown'),
                                'institute': topper_info.get('institute'),
                                'rank': topper_info.get('rank'),
                                'exam_year': topper_info.get('year'),
                                'source_document': topper_info.get('filename'),
                                'extraction_timestamp': datetime.now().isoformat()
                            })
                break
        
        logger.info(f"Fallback extraction found {len(qa_pairs)} Q&A pairs")
        return qa_pairs
    
    async def save_to_databases(self, qa_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save extracted data to both PostgreSQL and Milvus"""
        postgres_saved = 0
        milvus_saved = 0
        
        # Save to PostgreSQL
        db = SessionLocal()
        try:
            postgres_batch = []
            milvus_batch = []
            
            for qa in qa_data:
                # Create PostgreSQL record
                topper_ref = TopperReference(
                    topper_name=qa['topper_name'],
                    institute=qa.get('institute'),
                    exam_year=qa.get('exam_year'),
                    rank=qa.get('rank'),
                    question_id=qa['question_id'],
                    question_text=qa['question_text'],
                    subject=qa['subject'],
                    topic=qa.get('topic'),
                    marks=qa['estimated_marks'],
                    topper_answer_text=qa['answer_text'],
                    word_count=qa.get('word_count'),
                    source_document=qa.get('source_document'),
                    page_number=qa.get('page_references', [0])[0] if qa.get('page_references') else 1
                )
                
                db.add(topper_ref)
                postgres_batch.append(topper_ref)
            
            # Commit PostgreSQL batch
            db.commit()
            postgres_saved = len(postgres_batch)
            
            # Prepare Milvus data with database IDs
            for i, topper_ref in enumerate(postgres_batch):
                qa_item = qa_data[i]
                milvus_data = {
                    'topper_id': topper_ref.id,
                    'topper_name': topper_ref.topper_name,
                    'institute': topper_ref.institute,
                    'rank': topper_ref.rank,
                    'exam_year': topper_ref.exam_year,
                    'question_id': topper_ref.question_id,
                    'question_text': topper_ref.question_text,
                    'subject': topper_ref.subject,
                    'topic': topper_ref.topic,
                    'marks': topper_ref.marks,
                    'answer_text': topper_ref.topper_answer_text,
                    'word_count': topper_ref.word_count,
                    'source_document': topper_ref.source_document,
                    'page_number': topper_ref.page_number
                }
                milvus_batch.append(milvus_data)
            
            # Save to Milvus
            if milvus_batch:
                await topper_vector_service.bulk_insert_toppers(milvus_batch)
                milvus_saved = len(milvus_batch)
                
            logger.info(f"✅ Saved {postgres_saved} records to PostgreSQL, {milvus_saved} to Milvus")
            
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Database save failed: {e}")
        finally:
            db.close()
        
        return {"postgres": postgres_saved, "milvus": milvus_saved}
    
    def discover_topper_pdfs(self) -> List[Dict[str, Any]]:
        """Discover all topper PDFs in the upload directory and subdirectories"""
        topper_pdfs = []
        
        # Search patterns for topper files
        search_patterns = [
            "*topper*.pdf",
            "*Topper*.pdf", 
            "*TOPPER*.pdf",
            "*rank*.pdf",
            "*Rank*.pdf",
            "*AIR*.pdf",
            "*answer*booklet*.pdf",
            "*Answer*Booklet*.pdf"
        ]
        
        # Search in uploads directory and subdirectories
        for pattern in search_patterns:
            for pdf_file in self.upload_dir.rglob(pattern):
                if pdf_file.is_file():
                    # Extract topper info from filename
                    filename = pdf_file.name
                    topper_info = self._extract_topper_info_from_filename(filename)
                    topper_info['filepath'] = pdf_file
                    topper_info['filename'] = filename
                    topper_pdfs.append(topper_info)
        
        # Remove duplicates
        seen_files = set()
        unique_pdfs = []
        for pdf in topper_pdfs:
            if pdf['filepath'] not in seen_files:
                seen_files.add(pdf['filepath'])
                unique_pdfs.append(pdf)
        
        logger.info(f"📁 Discovered {len(unique_pdfs)} unique topper PDF files")
        return unique_pdfs
    
    def _extract_topper_info_from_filename(self, filename: str) -> Dict[str, Any]:
        """Extract topper information from filename patterns"""
        import re
        
        # Default values
        info = {
            'name': 'Unknown',
            'institute': None,
            'rank': None,
            'year': 2024
        }
        
        # Extract name patterns
        name_patterns = [
            r'([A-Za-z\s]+)(?:_|\s+)(?:topper|Topper|TOPPER)',
            r'(?:topper|Topper|TOPPER)(?:_|\s+)([A-Za-z\s]+)',
            r'([A-Za-z]+(?:\s+[A-Za-z]+){1,2})(?:_|\s+)',  # General name pattern
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, filename)
            if match:
                info['name'] = match.group(1).strip().title()
                break
        
        # Extract rank patterns
        rank_patterns = [
            r'(?:rank|Rank|RANK|AIR)(?:_|\s+)(\d+)',
            r'(\d+)(?:_|\s+)(?:rank|Rank|RANK)',
            r'AIR[\s_]*(\d+)'
        ]
        
        for pattern in rank_patterns:
            match = re.search(pattern, filename)
            if match:
                info['rank'] = int(match.group(1))
                break
        
        # Extract year patterns
        year_patterns = [
            r'(20\d{2})',
            r'(\d{4})'
        ]
        
        for pattern in year_patterns:
            matches = re.findall(pattern, filename)
            for match in matches:
                year = int(match)
                if 2010 <= year <= 2025:
                    info['year'] = year
                    break
        
        return info
    
    async def process_all_toppers(self) -> Dict[str, Any]:
        """Process all discovered topper PDFs"""
        logger.info("🚀 Starting batch topper processing...")
        
        # Discover all topper PDFs
        topper_pdfs = self.discover_topper_pdfs()
        
        if not topper_pdfs:
            logger.warning("⚠️  No topper PDFs found in upload directory")
            return {"status": "no_files", "processed": 0}
        
        logger.info(f"📚 Found {len(topper_pdfs)} topper PDFs to process")
        
        # Process in batches for efficiency
        batch_size = 5  # Process 5 PDFs at a time
        total_processed = 0
        total_qa_pairs = 0
        
        for i in range(0, len(topper_pdfs), batch_size):
            batch = topper_pdfs[i:i+batch_size]
            logger.info(f"📦 Processing batch {i//batch_size + 1}/{(len(topper_pdfs)-1)//batch_size + 1}")
            
            # Process batch
            batch_tasks = []
            for pdf_info in batch:
                task = self.extract_from_single_pdf(pdf_info['filepath'], pdf_info)
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Process results
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Failed to process {batch[j]['filename']}: {result}")
                    self.failed_count += 1
                else:
                    if result:  # Non-empty result
                        # Save to databases
                        save_stats = await self.save_to_databases(result)
                        total_qa_pairs += save_stats.get('postgres', 0)
                        logger.info(f"✅ Processed {batch[j]['filename']}: {len(result)} Q&A pairs")
                    
                    self.processed_count += 1
        
        # Final statistics
        final_stats = await topper_vector_service.get_collection_stats()
        
        summary = {
            "status": "completed",
            "total_pdfs_found": len(topper_pdfs),
            "successfully_processed": self.processed_count,
            "failed_processing": self.failed_count,
            "total_qa_pairs_extracted": total_qa_pairs,
            "final_database_stats": final_stats,
            "processing_duration": "See logs for timing"
        }
        
        logger.info(f"🎉 Batch processing completed: {summary}")
        return summary

async def main():
    """Main execution function"""
    logger.info("🎯 Enhanced Topper Content Extraction with Vector Search")
    logger.info("=" * 60)
    
    extractor = EnhancedTopperExtractor()
    
    try:
        # Initialize services
        await extractor.initialize_services()
        
        # Process all topper PDFs
        results = await extractor.process_all_toppers()
        
        # Display results
        print("\n" + "="*60)
        print("📊 EXTRACTION SUMMARY")
        print("="*60)
        for key, value in results.items():
            print(f"{key}: {value}")
        
        print("\n✅ Enhanced topper extraction completed successfully!")
        print("🔍 You can now use vector similarity search to find relevant topper answers")
        print("📈 The 14th dimension analysis will leverage this data for better insights")
        
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}")
        print(f"\n💥 Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
