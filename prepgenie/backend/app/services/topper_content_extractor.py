"""
Topper Content Extraction Service
Extracts and processes topper answers from PDF documents for analysis and comparison
"""
import logging
import json
import os
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.core.llm_service import get_llm_service, LLMService
from app.models.topper_reference import TopperReference, TopperPattern
from app.schemas.topper_reference import TopperReferenceCreate
from app.utils.vision_pdf_processor import VisionPDFProcessor
from app.services.topper_analysis_service import TopperAnalysisService

logger = logging.getLogger(__name__)

class TopperContentExtractor:
    """Service for extracting topper content from PDF documents"""
    
    def __init__(self, llm_service: LLMService = None):
        self.llm_service = llm_service or get_llm_service()
        self.topper_analysis_service = TopperAnalysisService(llm_service)
    
    async def extract_topper_content_from_pdf(self, 
                                            pdf_path: str, 
                                            topper_name: str,
                                            institute: str = None,
                                            exam_year: int = None,
                                            rank: int = None) -> Dict:
        """
        Extract topper's questions and answers from PDF using vision processing
        """
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting topper content from: {pdf_path}")
        
        try:
            # Use existing vision PDF processor
            processor = VisionPDFProcessor()
            extraction_result = await processor.process_pdf_with_vision(pdf_path)
            
            if not extraction_result or 'questions' not in extraction_result:
                logger.warning("No questions extracted from topper PDF")
                return {"success": False, "error": "No content extracted"}
            
            # Process each question-answer pair
            topper_references = []
            extracted_questions = extraction_result['questions']
            
            logger.info(f"Processing {len(extracted_questions)} topper question-answer pairs")
            
            for i, qa_pair in enumerate(extracted_questions):
                try:
                    # Extract basic information
                    question_text = qa_pair.get('question_text', '')
                    student_answer = qa_pair.get('student_answer', '')  # This is actually topper's answer
                    marks = qa_pair.get('marks', 15)
                    page_number = qa_pair.get('page_number', i + 1)
                    
                    if not question_text or not student_answer:
                        logger.warning(f"Skipping incomplete Q&A pair {i+1}")
                        continue
                    
                    # Determine subject from question content
                    subject = await self._determine_subject(question_text)
                    
                    # Analyze the topper's answer for patterns
                    answer_analysis = await self.topper_analysis_service.analyze_topper_answer_patterns(
                        topper_answer=student_answer,
                        question=question_text,
                        subject=subject,
                        marks=marks
                    )
                    
                    # Create topper reference record
                    topper_ref = TopperReferenceCreate(
                        topper_name=topper_name,
                        institute=institute,
                        exam_year=exam_year,
                        rank=rank,
                        question_id=f"topper_{topper_name.lower().replace(' ', '_')}_{i+1}",
                        question_text=question_text,
                        subject=subject,
                        topic=await self._extract_topic(question_text, subject),
                        marks=marks,
                        topper_answer_text=student_answer,
                        word_count=len(student_answer.split()),
                        answer_analysis=answer_analysis,
                        source_document=pdf_path,
                        page_number=page_number
                    )
                    
                    topper_references.append(topper_ref)
                    logger.info(f"Successfully processed topper Q&A {i+1}: {subject} - {marks} marks")
                    
                except Exception as e:
                    logger.error(f"Error processing topper Q&A {i+1}: {e}")
                    continue
            
            return {
                "success": True,
                "topper_references": topper_references,
                "total_extracted": len(topper_references),
                "source_document": pdf_path
            }
            
        except Exception as e:
            logger.error(f"Error extracting topper content: {e}")
            return {"success": False, "error": str(e)}
    
    async def save_topper_references(self, 
                                   topper_references: List[TopperReferenceCreate], 
                                   db: Session) -> Dict:
        """
        Save extracted topper references to database
        """
        
        saved_count = 0
        errors = []
        
        for topper_ref in topper_references:
            try:
                # Create database record
                db_topper_ref = TopperReference(**topper_ref.dict())
                db.add(db_topper_ref)
                db.commit()
                db.refresh(db_topper_ref)
                
                saved_count += 1
                logger.info(f"Saved topper reference {db_topper_ref.id}: {topper_ref.subject}")
                
            except Exception as e:
                logger.error(f"Error saving topper reference: {e}")
                errors.append(str(e))
                db.rollback()
                continue
        
        return {
            "saved_count": saved_count,
            "total_references": len(topper_references),
            "errors": errors
        }
    
    async def extract_and_save_topper_patterns(self, 
                                             topper_references: List[TopperReference], 
                                             db: Session) -> Dict:
        """
        Extract common patterns from multiple topper answers and save them
        """
        
        if not topper_references:
            return {"success": False, "error": "No topper references provided"}
        
        # Group references by subject for pattern analysis
        subject_groups = {}
        for ref in topper_references:
            if ref.subject not in subject_groups:
                subject_groups[ref.subject] = []
            subject_groups[ref.subject].append(ref)
        
        extracted_patterns = []
        
        for subject, refs in subject_groups.items():
            try:
                # Extract patterns for this subject
                subject_patterns = await self._extract_subject_patterns(subject, refs)
                extracted_patterns.extend(subject_patterns)
                
            except Exception as e:
                logger.error(f"Error extracting patterns for {subject}: {e}")
                continue
        
        # Save patterns to database
        saved_patterns = 0
        for pattern in extracted_patterns:
            try:
                db_pattern = TopperPattern(**pattern)
                db.add(db_pattern)
                db.commit()
                saved_patterns += 1
                
            except Exception as e:
                logger.error(f"Error saving pattern: {e}")
                db.rollback()
                continue
        
        return {
            "success": True,
            "patterns_extracted": len(extracted_patterns),
            "patterns_saved": saved_patterns,
            "subjects_analyzed": list(subject_groups.keys())
        }
    
    async def _determine_subject(self, question_text: str) -> str:
        """
        Determine UPSC subject from question text
        """
        
        subject_prompt = f"""Determine the UPSC subject for this question:

Question: {question_text}

Return only one of these exact values:
- GS-I
- GS-II  
- GS-III
- GS-IV
- Essay

Choose the most appropriate subject based on the question content."""

        try:
            response = await self.llm_service.simple_chat(
                user_message=subject_prompt,
                temperature=0.1
            )
            
            subject = response.strip()
            if subject in ["GS-I", "GS-II", "GS-III", "GS-IV", "Essay"]:
                return subject
            else:
                return "GS-II"  # Default fallback
                
        except Exception as e:
            logger.error(f"Error determining subject: {e}")
            return "GS-II"  # Default fallback
    
    async def _extract_topic(self, question_text: str, subject: str) -> Optional[str]:
        """
        Extract specific topic from question text
        """
        
        topic_prompt = f"""Extract the main topic/theme from this {subject} question:

Question: {question_text}

Return a concise topic name (2-4 words) that captures the main theme."""

        try:
            response = await self.llm_service.simple_chat(
                user_message=topic_prompt,
                temperature=0.2
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error extracting topic: {e}")
            return None
    
    async def _extract_subject_patterns(self, 
                                      subject: str, 
                                      topper_refs: List[TopperReference]) -> List[Dict]:
        """
        Extract common patterns from topper answers in a specific subject
        """
        
        if len(topper_refs) < 2:
            return []  # Need at least 2 answers to identify patterns
        
        # Prepare analysis data
        answers_data = []
        for ref in topper_refs:
            answers_data.append({
                "question": ref.question_text,
                "answer": ref.topper_answer_text,
                "marks": ref.marks,
                "analysis": ref.answer_analysis
            })
        
        pattern_prompt = f"""Analyze these {len(topper_refs)} topper answers from {subject} to identify common high-scoring patterns:

{json.dumps(answers_data, indent=2)}

Identify recurring patterns and return in JSON format:

{{
    "structural_patterns": [
        {{
            "pattern_type": "structure",
            "pattern_name": "Introduction-Body-Conclusion Framework",
            "description": "Detailed description of the pattern",
            "frequency": 0.8,
            "effectiveness_score": 8.5,
            "examples": ["Example 1", "Example 2"]
        }}
    ],
    "content_patterns": [
        {{
            "pattern_type": "content",
            "pattern_name": "Multi-dimensional Analysis",
            "description": "How toppers approach multi-faceted questions",
            "frequency": 0.7,
            "effectiveness_score": 9.0,
            "examples": ["Example usage"]
        }}
    ],
    "writing_patterns": [
        {{
            "pattern_type": "writing",
            "pattern_name": "Analytical Language Use",
            "description": "Specific language patterns that enhance scoring",
            "frequency": 0.9,
            "effectiveness_score": 8.0,
            "examples": ["Example phrases/structures"]
        }}
    ]
}}"""

        try:
            response = await self.llm_service.simple_chat(
                user_message=pattern_prompt,
                temperature=0.3
            )
            
            patterns_data = json.loads(response)
            
            # Convert to database format
            db_patterns = []
            
            for pattern_category in ["structural_patterns", "content_patterns", "writing_patterns"]:
                if pattern_category in patterns_data:
                    for pattern in patterns_data[pattern_category]:
                        db_pattern = {
                            "pattern_type": pattern.get("pattern_type", "general"),
                            "pattern_name": pattern.get("pattern_name", "Unknown Pattern"),
                            "description": pattern.get("description", ""),
                            "subjects": [subject],
                            "frequency": pattern.get("frequency", 0.5),
                            "effectiveness_score": pattern.get("effectiveness_score", 7.0),
                            "examples": pattern.get("examples", []),
                            "references": [ref.id for ref in topper_refs if ref.id]
                        }
                        db_patterns.append(db_pattern)
            
            return db_patterns
            
        except Exception as e:
            logger.error(f"Error extracting subject patterns: {e}")
            return []

# Global instance
topper_content_extractor = TopperContentExtractor()
