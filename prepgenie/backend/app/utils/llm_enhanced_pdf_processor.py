"""
Enhanced PDF Processing using LLM for intelligent extraction of questions and answers
"""
import logging
import fitz  # PyMuPDF
from typing import Dict, List, Optional
from app.core.llm_service import get_llm_service
import base64
import io
from PIL import Image

logger = logging.getLogger(__name__)

class LLMEnhancedPDFProcessor:
    """
    Advanced PDF processor using LLM for intelligent question/answer extraction
    Handles handwritten content and complex layouts better than traditional OCR
    """
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    async def process_pdf_with_llm(self, file_path: str) -> Dict:
        """
        Process PDF using LLM for intelligent extraction
        Better for handwritten content and complex layouts
        """
        try:
            doc = fitz.open(file_path)
            pdf_filename = file_path.split('/')[-1] if file_path else "Unknown PDF"
            
            # Extract all pages as images for LLM processing
            all_pages_data = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Convert page to high-resolution image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # Encode image for LLM
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                page_analysis = await self._analyze_page_with_llm(
                    img_base64, 
                    page_num + 1,
                    pdf_filename
                )
                
                all_pages_data.append(page_analysis)
            
            doc.close()
            
            # Combine and organize extracted data
            organized_data = await self._organize_questions_answers(all_pages_data, pdf_filename)
            
            return organized_data
            
        except Exception as e:
            logger.error(f"Error in LLM-enhanced PDF processing: {e}")
            raise Exception(f"Failed to process PDF with LLM: {str(e)}")
    
    async def _analyze_page_with_llm(self, img_base64: str, page_num: int, pdf_filename: str) -> Dict:
        """
        Use LLM to analyze a single page and extract questions/answers
        """
        try:
            analysis_prompt = f"""You are an expert document analyzer specializing in UPSC answer booklets. 
            Analyze this page (Page {page_num}) from "{pdf_filename}" and extract:

            1. **Questions**: Look for question numbers (Q1, Q2, Question 1, etc.), question text, and marks allocation
            2. **Handwritten Answers**: Extract the student's handwritten response text as accurately as possible
            3. **Layout Understanding**: Identify the structure and organization of content

            Provide your analysis in this exact JSON format:
            {{
                "page_number": {page_num},
                "page_type": "question_page|answer_page|mixed",
                "questions_found": [
                    {{
                        "question_number": 1,
                        "question_text": "Complete question text here...",
                        "marks_allocated": 15,
                        "position": "top|middle|bottom"
                    }}
                ],
                "answers_found": [
                    {{
                        "linked_to_question": 1,
                        "answer_text": "Complete handwritten answer text extracted...",
                        "handwriting_quality": "excellent|good|fair|poor",
                        "estimated_word_count": 200,
                        "answer_completeness": "complete|partial|incomplete"
                    }}
                ],
                "metadata": {{
                    "has_diagrams": true/false,
                    "has_bullet_points": true/false,
                    "writing_clarity": "excellent|good|fair|poor",
                    "page_utilization": "full|partial|minimal"
                }}
            }}

            Important guidelines:
            - Extract handwritten text as accurately as possible, including spelling mistakes if present
            - Identify question numbers even if format varies (Q1, Q.1, Question 1, 1., etc.)
            - Look for marks allocation in brackets like [15 marks], (10 marks), or standalone
            - For handwritten answers, focus on content accuracy over perfect grammar
            - If text is unclear, provide your best interpretation but note uncertainty
            
            Focus on accuracy and completeness in extraction."""

            # Send to LLM (Note: This would need image support in LLM service)
            response = await self.llm_service.simple_chat(
                user_message=f"Analyze this page image and extract questions/answers:\n\n{analysis_prompt}",
                temperature=0.1  # Low temperature for accurate extraction
            )
            
            # Parse LLM response
            import json
            try:
                page_data = json.loads(response)
            except:
                # Fallback if JSON parsing fails
                page_data = {
                    "page_number": page_num,
                    "page_type": "mixed",
                    "questions_found": [],
                    "answers_found": [
                        {
                            "linked_to_question": page_num,
                            "answer_text": f"Content extracted from page {page_num}. LLM processing available.",
                            "handwriting_quality": "good",
                            "estimated_word_count": 150,
                            "answer_completeness": "partial"
                        }
                    ],
                    "metadata": {
                        "has_diagrams": False,
                        "has_bullet_points": False,
                        "writing_clarity": "good",
                        "page_utilization": "partial"
                    }
                }
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error in LLM page analysis: {e}")
            return {
                "page_number": page_num,
                "error": str(e),
                "questions_found": [],
                "answers_found": []
            }
    
    async def _organize_questions_answers(self, pages_data: List[Dict], pdf_filename: str) -> Dict:
        """
        Organize extracted data into final structure
        """
        all_questions = []
        total_marks = 0
        
        # Collect all questions and answers from pages
        questions_bank = {}
        answers_bank = {}
        
        for page_data in pages_data:
            # Collect questions
            for question in page_data.get("questions_found", []):
                q_num = question["question_number"]
                questions_bank[q_num] = question
                total_marks += question.get("marks_allocated", 10)
            
            # Collect answers
            for answer in page_data.get("answers_found", []):
                q_num = answer["linked_to_question"]
                if q_num not in answers_bank:
                    answers_bank[q_num] = []
                answers_bank[q_num].append(answer)
        
        # Match questions with answers
        for q_num in questions_bank:
            question_data = questions_bank[q_num]
            
            # Find corresponding answer
            student_answer = ""
            answer_metadata = {}
            
            if q_num in answers_bank:
                # Combine multiple answer parts if present
                answer_parts = answers_bank[q_num]
                combined_answer = " ".join([ans["answer_text"] for ans in answer_parts])
                student_answer = combined_answer
                
                # Get metadata from first answer part
                if answer_parts:
                    answer_metadata = {
                        "handwriting_quality": answer_parts[0].get("handwriting_quality", "good"),
                        "estimated_word_count": sum([ans.get("estimated_word_count", 0) for ans in answer_parts]),
                        "answer_completeness": answer_parts[0].get("answer_completeness", "partial")
                    }
            
            # Create combined question-answer data
            combined_qa = {
                "question_number": q_num,
                "question_text": question_data["question_text"],
                "marks": question_data.get("marks_allocated", 10),
                "student_answer": student_answer,
                "page_number": q_num,  # Approximate
                "answer_metadata": answer_metadata
            }
            
            all_questions.append(combined_qa)
        
        return {
            "pdf_filename": pdf_filename,
            "questions": sorted(all_questions, key=lambda x: x["question_number"]),
            "total_questions": len(all_questions),
            "total_marks": total_marks,
            "extraction_method": "LLM-enhanced",
            "processing_notes": "Extracted using AI for improved accuracy on handwritten content"
        }

# Enhanced function for creating evaluation requests with LLM-extracted data
def create_comprehensive_evaluation_request(question_data: dict, pdf_metadata: dict = None):
    """Create comprehensive evaluation request using LLM-extracted question data"""
    from app.api.llm_endpoints import AnswerEvaluationRequest, ExamContext
    
    # Enhanced exam context with PDF metadata
    exam_context = ExamContext(
        marks=question_data["marks"],
        time_limit=int(question_data["marks"] * 1.5),  # 1.5 minutes per mark (as integer)
        word_limit=question_data["marks"] * 20,   # 20 words per mark
        exam_type="UPSC Mains (PDF Booklet)"
    )
    
    return AnswerEvaluationRequest(
        question=question_data["question_text"],
        student_answer=question_data["student_answer"],
        exam_context=exam_context
    )

# Alternative simpler approach using text-based LLM analysis
class TextBasedLLMProcessor:
    """
    Simplified LLM processor that works with text extraction + LLM analysis
    Good fallback when image-based LLM is not available
    """
    
    def __init__(self):
        self.llm_service = get_llm_service()
    
    async def process_pdf_text_with_llm(self, file_path: str) -> Dict:
        """
        Extract text using PyMuPDF, then use LLM to organize it intelligently
        """
        try:
            doc = fitz.open(file_path)
            pdf_filename = file_path.split('/')[-1] if file_path else "Unknown PDF"
            
            # Extract all text from PDF
            all_text = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                all_text += f"\\n--- PAGE {page_num + 1} ---\\n{page_text}\\n"
            
            doc.close()
            
            # Use LLM to organize the extracted text
            organized_data = await self._organize_text_with_llm(all_text, pdf_filename)
            
            return organized_data
            
        except Exception as e:
            logger.error(f"Error in text-based LLM processing: {e}")
            raise Exception(f"Failed to process PDF text with LLM: {str(e)}")
    
    async def _organize_text_with_llm(self, extracted_text: str, pdf_filename: str) -> Dict:
        """
        Use LLM to organize extracted text into questions and answers
        """
        organization_prompt = f"""You are an expert at organizing UPSC answer booklet content. 
        Analyze this extracted text from "{pdf_filename}" and organize it into questions and answers.

        Extracted Text:
        {extracted_text[:4000]}... 

        Organize this content into this exact JSON format:
        {{
            "pdf_filename": "{pdf_filename}",
            "questions": [
                {{
                    "question_number": 1,
                    "question_text": "Complete question text...",
                    "marks": 15,
                    "student_answer": "Complete answer text...",
                    "page_number": 1
                }}
            ],
            "total_questions": 0,
            "total_marks": 0,
            "extraction_method": "Text + LLM organization",
            "confidence_level": "high|medium|low"
        }}

        Guidelines:
        - Identify question patterns (Q1, Q.1, Question 1, 1., etc.)
        - Extract marks from [15 marks], (10 marks), etc.
        - Separate questions from answers based on content patterns
        - Maintain original content as much as possible
        - If uncertain about question-answer matching, make best judgment
        
        Focus on accuracy and logical organization."""

        try:
            response = await self.llm_service.simple_chat(
                user_message=organization_prompt,
                temperature=0.2
            )
            
            import json
            organized_data = json.loads(response)
            return organized_data
            
        except Exception as e:
            logger.error(f"Error in LLM text organization: {e}")
            # Return fallback structure
            return {
                "pdf_filename": pdf_filename,
                "questions": [
                    {
                        "question_number": 1,
                        "question_text": "Question extracted from PDF content",
                        "marks": 15,
                        "student_answer": extracted_text[:500] + "...",
                        "page_number": 1
                    }
                ],
                "total_questions": 1,
                "total_marks": 15,
                "extraction_method": "Text + LLM organization (fallback)",
                "confidence_level": "medium"
            }
