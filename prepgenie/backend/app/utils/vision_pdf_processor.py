#!/usr/bin/env python3
"""
Vision-based PDF Processor for 13-Dimensional Evaluation System
Integrates vision extraction with comprehe    return AnswerEvaluationRequest(
        question=question_data["question_text"],
        student_answer=question_data["student_answer"],
        exam_context=ExamContext(
            marks=marks,
            time_limit=int((marks or 10) * 1.5),  # 1.5 minutes per mark (as integer)
            word_limit=(marks or 10) * 20,  # 20 words per mark  
            exam_type="UPSC Mains"
        )
    )er evaluation
Enhanced with real-time progress tracking for better UX
"""

import sys
import os
import logging
import asyncio
import fitz  # PyMuPDF for PDF page conversion
import base64
import json
from io import BytesIO
from PIL import Image
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from sqlalchemy.orm import Session

# Import core services
from app.core.llm_service import get_llm_service, LLMService
from app.api.llm_endpoints import (
    AnswerEvaluationRequest, ExamContext, evaluate_answer,
    comprehensive_question_analysis_direct
)

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Track and report processing progress with time estimates"""
    
    def __init__(self, total_pages: int, callback: Optional[Callable] = None):
        self.total_pages = total_pages
        self.current_page = 0
        self.current_question = 0
        self.total_questions = 0
        self.start_time = datetime.now()
        self.phase = "initializing"
        self.callback = callback
        
        # Time estimates (in seconds per page)
        self.time_estimates = {
            "page_processing": 15,  # 15 seconds per page for vision analysis
            "question_extraction": 10,  # 10 seconds per page for question detection
            "answer_evaluation": 30,  # 30 seconds per question for comprehensive evaluation
        }
    
    def estimate_total_time(self) -> int:
        """Estimate total processing time in minutes"""
        page_time = self.total_pages * (self.time_estimates["page_processing"] + self.time_estimates["question_extraction"])
        # Estimate 2-3 questions per page on average
        estimated_questions = self.total_pages * 2.5
        question_time = estimated_questions * self.time_estimates["answer_evaluation"]
        total_seconds = page_time + question_time
        return int(total_seconds / 60) + 1  # Round up to next minute
    
    async def update_progress(self, phase: str, current_page: int = None, current_question: int = None, 
                       total_questions: int = None, details: str = ""):
        """Update progress and notify callback"""
        self.phase = phase
        if current_page is not None:
            self.current_page = current_page
        if current_question is not None:
            self.current_question = current_question
        if total_questions is not None:
            self.total_questions = total_questions
        
        # Calculate progress percentage with proper bounds checking
        if phase == "page_processing":
            if current_page and self.total_pages > 0:
                progress = int((current_page / self.total_pages) * 30)  # 0% to 30% for page processing
            else:
                progress = 0
        elif phase == "question_extraction":
            if current_page and self.total_pages > 0:
                progress = 30 + int((current_page / self.total_pages) * 20)  # 30% to 50% for extraction
            else:
                progress = 30
        elif phase == "answer_evaluation":
            if self.total_questions > 0 and current_question:
                progress = 50 + int((current_question / self.total_questions) * 50)  # 50% to 100% for evaluation
            else:
                progress = 50
        elif phase == "finalizing":
            progress = 100  # Always show 100% for finalizing
        else:
            progress = 0
        
        # Calculate estimated time remaining with better logic
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if phase == "finalizing":
            remaining = 0  # No time remaining when finalizing
        elif progress > 5:  # Only calculate if we have meaningful progress
            estimated_total = elapsed * 100 / max(progress, 5)  # Avoid division issues
            remaining = max(0, int((estimated_total - elapsed) / 60))
        else:
            remaining = self.estimate_total_time()
        
        message = self._format_message(phase, current_page, current_question, details, remaining)
        
        # Log progress
        logger.info(f"Progress: {progress}% - {message}")
        
        # Call callback if provided (handle both sync and async callbacks)
        if self.callback:
            print(f"🔧 DEBUG: ProgressTracker callback found, preparing to call it")
            logger.info(f"🔧 DEBUG: ProgressTracker callback found, preparing to call it")
            
            callback_data = {
                "phase": phase,
                "progress": progress,
                "current_page": current_page,
                "current_question": current_question,
                "total_pages": self.total_pages,
                "total_questions": self.total_questions,
                "message": message,
                "estimated_remaining_minutes": remaining,
                "details": details
            }
            
            print(f"⚡ DEBUG: About to call callback with data: {callback_data}")
            logger.info(f"⚡ DEBUG: About to call callback with data: {callback_data}")
            
            # Check if callback is async or sync
            import asyncio
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    print(f"🔄 DEBUG: Calling ASYNC callback")
                    await self.callback(callback_data)
                    print(f"✅ DEBUG: ASYNC callback completed successfully")
                else:
                    print(f"🔄 DEBUG: Calling SYNC callback")
                    self.callback(callback_data)
                    print(f"✅ DEBUG: SYNC callback completed successfully")
            except Exception as callback_error:
                print(f"💥 DEBUG: Callback execution failed: {callback_error}")
                logger.error(f"💥 DEBUG: Callback execution failed: {callback_error}")
                import traceback
                traceback.print_exc()
        else:
            print(f"❌ DEBUG: No callback provided to ProgressTracker!")
            logger.warning(f"❌ DEBUG: No callback provided to ProgressTracker!")
    
    def _format_message(self, phase: str, current_page: int, current_question: int, 
                       details: str, remaining_minutes: int) -> str:
        """Format user-friendly progress message"""
        if phase == "page_processing":
            return f"📄 Processing page {current_page}/{self.total_pages} - Analyzing content with AI vision (~{remaining_minutes} min remaining)"
        elif phase == "question_extraction":
            return f"🔍 Extracting questions from page {current_page}/{self.total_pages} - Identifying question patterns (~{remaining_minutes} min remaining)"
        elif phase == "answer_evaluation":
            return f"⭐ Evaluating Question {current_question}/{self.total_questions} - {details} (~{remaining_minutes} min remaining)"
        elif phase == "finalizing":
            return f"✨ Finalizing comprehensive evaluation - Almost done! (~{remaining_minutes} min remaining)"
        else:
            return f"🚀 Starting PDF processing - {self.total_pages} pages detected (~{remaining_minutes} min estimated)"

# Utility functions for compatibility with existing code
def create_question_specific_evaluation_request(question_data: dict):
    """Create evaluation request for a specific question from PDF processing"""
    marks = question_data.get("marks", 10) or 10  # Default to 10 if marks is None
    return AnswerEvaluationRequest(
        question=question_data["question_text"],
        student_answer=question_data["student_answer"],
        exam_context=ExamContext(
            marks=marks,
            time_limit=int((marks or 10) * 1.5),  # 1.5 minutes per mark (as integer)
            word_limit=(marks or 10) * 20,   # 20 words per mark
            exam_type="UPSC Mains"
        )
    )

def extract_questions_from_pdf(file_path: str) -> Dict:
    """Extract questions from PDF using vision processor - compatibility function"""
    async def _extract():
        processor = VisionPDFProcessor()
        return await processor.process_pdf_with_vision(file_path)
    
    return asyncio.run(_extract())

class VisionPDFProcessor:
    """
    Advanced PDF processor using vision-capable LLM for handwritten content extraction
    Integrated with 13-dimensional evaluation system with progress tracking
    """
    
    def __init__(self, progress_callback=None, llm_service=None):
        print(f"DEBUG: VisionPDFProcessor.__init__ called with args: progress_callback={progress_callback}, llm_service={llm_service}")
        print(f"DEBUG: Arguments received in __init__: {locals()}")
        # Ignore llm_service parameter for compatibility - we get our own
        self.llm_service = get_llm_service()
        self.extracted_questions = []
        self.extracted_answers = []
        self.evaluation_results = []
        self.progress_callback = progress_callback
        self.total_pages = 0
        self.current_page = 0
        self.processing_start_time = None
    
    async def log_progress(self, message: str, progress_type: str = "info", details: dict = None):
        """Log progress with structured information for UI and logs"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Log to server
        logger.info(f"[{timestamp}] {message}")
        
        # If progress callback is provided, send structured data to UI
        if self.progress_callback:
            progress_data = {
                "timestamp": timestamp,
                "message": message,
                "type": progress_type,
                "current_page": self.current_page,
                "total_pages": self.total_pages,
                "progress_percentage": int((self.current_page / max(self.total_pages, 1)) * 100),
                "details": details or {}
            }
            await self.progress_callback(progress_data)
    
    def estimate_processing_time(self, total_pages: int, pdf_size_mb: float) -> dict:
        """Estimate processing time based on page count and file size"""
        # Base processing time per page (2-3 minutes average)
        base_time_per_page = 2.5  # minutes
        
        # Adjust for file size - larger files may have higher quality images
        size_factor = 1.0
        if pdf_size_mb > 10:
            size_factor = 1.3
        elif pdf_size_mb > 5:
            size_factor = 1.1
        
        # Calculate estimated time
        estimated_minutes = total_pages * base_time_per_page * size_factor
        estimated_seconds = int(estimated_minutes * 60)
        
        return {
            "total_pages": total_pages,
            "estimated_minutes": round(estimated_minutes, 1),
            "estimated_seconds": estimated_seconds,
            "size_mb": pdf_size_mb,
            "time_per_page_minutes": round(base_time_per_page * size_factor, 1)
        }
        
    def convert_page_to_image(self, page) -> str:
        """Convert PDF page to base64 encoded image for vision analysis"""
        try:
            # Render page as image with high quality
            mat = fitz.Matrix(2.0, 2.0)  # Higher resolution for better text recognition
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Convert to PIL Image for any processing if needed
            img = Image.open(BytesIO(img_data))
            
            # Convert to base64
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            return img_b64
            
        except Exception as e:
            logger.error(f"Error converting page to image: {e}")
            return ""
    
    async def analyze_page_with_vision(self, page_image: str, page_num: int) -> Dict:
        """Analyze a single page using vision-capable LLM with enhanced UPSC-specific prompt"""
        
        vision_prompt = """🎓 **UPSC MAINS HANDWRITTEN ANSWER BOOKLET ANALYZER** 🎓

You are analyzing a **HANDWRITTEN UPSC Civil Services Mains exam answer booklet** written by competitive exam students. This is a comprehensive evaluation of student responses on Indian governance, polity, economics, society, international relations, and current affairs.

🎯 **CRITICAL CONTEXT**: 
- This is a **STUDENT'S HANDWRITTEN ANSWER BOOKLET** for UPSC CSE Mains exam
- Students write detailed analytical responses across multiple pages for each question
- Answers demonstrate policy understanding, constitutional knowledge, and current affairs integration
- Students frequently use visual aids (diagrams, flowcharts, tables, maps) to enhance their presentation
- Handwriting varies from clear to moderate difficulty - extract ALL visible content

📊 **VISUAL ELEMENTS STUDENTS COMMONLY INCLUDE**:
- **📊 Tables/Matrices**: Comparative analysis (Central vs State, Pros vs Cons, Before vs After)
- **🔄 Flowcharts**: Policy implementation flows (Scheme → Implementation → Monitoring → Impact)
- **🗺️ Maps & Sketches**: India map, state boundaries, international borders, geographic regions
- **🏛️ Organizational Charts**: Government structure (President → PM → Ministers → Departments)
- **📈 Graphs/Charts**: Economic indicators, demographic trends, statistical data presentation
- **⏰ Timelines**: Historical evolution (1947→1991→2014→2024), policy development phases
- **🧠 Mind Maps**: Concept interconnections, cause-effect relationships, issue-solution mapping
- **⚖️ Constitutional Diagrams**: Article relationships, fundamental rights structure, separation of powers
- **🌐 Process Diagrams**: Economic frameworks, international relations, administrative procedures
- **📋 Bullet Points & Lists**: Structured presentation of multiple points, schemes, policies

🔍 **EXTRACT WITH MAXIMUM PRECISION**:

**1. UPSC QUESTIONS** (Look for ANY of these question numbering patterns):
   - **Question Numbers**: Recognize ANY format like:
     * Standard: "1.", "2.", "3.", "Question 1.", "Question 2."
     * Abbreviated: "Q1.", "Q2.", "Q3.", "Que1.", "Que2."
     * Parentheses: "1)", "2)", "3)", "(1)", "(2)", "(3)"
     * Circled: "①", "②", "③" or numbers inside circles/boxes
     * Alternative: "1/", "Q1/", "Que1/" or any numbering variation
   - **Complete Question Text**: Extract entire question including ALL sub-parts: (a), (b), (c), (d)
   - **Word Limits**: "(150 words)", "(250 words)", "(300 words)", "word limit: 150"
   - **Marks Allocation**: "[10 marks]", "(15 marks)", "20M", "marks: 10"
   - **UPSC Keywords**: "Discuss", "Analyze", "Examine", "Critically evaluate", "Comment", "Elaborate"

**2. STUDENT HANDWRITTEN ANSWERS** (Comprehensive Extraction):

   **📝 TEXTUAL CONTENT** (Extract ALL readable text):
   - Complete paragraphs with policy analysis and constitutional references
   - **Government Schemes**: PM-KISAN, MGNREGA, POSHAN, Digital India, Ayushman Bharat, PLI schemes
   - **Constitutional Articles**: Article 356, Article 370, Article 14, Article 21, DPSPs, Fundamental Rights
   - **Legislative Acts**: RTI Act 2005, SARFAESI Act, IBC 2016, CAA, Farm Laws, GST Acts
   - **Current Affairs**: G20 presidency, COP28, Make in India, Atmanirbhar Bharat, NEP 2020
   - **International Relations**: QUAD, BRICS, SCO, Indo-Pacific, India-China relations, neighborhood policy
   - **Economic Policies**: Demonetization, GST implementation, FDI policies, fiscal federalism
   - **Social Issues**: Gender equality, caste dynamics, urbanization, digital divide, healthcare access

   **🎨 VISUAL ELEMENTS** (Detailed Description Required):
   - **Tables**: "3x4 table comparing Centre vs State functions with examples in each cell"
   - **Flowcharts**: "5-step flowchart: Policy Formulation → Approval → Implementation → Monitoring → Evaluation"
   - **Maps**: "Hand-drawn India map highlighting northeastern states with state names labeled"
   - **Organizational Charts**: "Government hierarchy: President → PM → Council of Ministers → Secretaries"
   - **Timelines**: "1947 Independence → 1991 Liberalization → 2014 Digital India → 2020 Atmanirbhar"
   - **Statistical Charts**: "Bar graph showing GDP growth 2019-2024 with percentages"
   - **Mind Maps**: "Central concept 'Federalism' with 6 branches: fiscal, administrative, legislative, judicial, cooperative, competitive"

   **🔗 CRITICAL: ANSWER CONTINUATION TRACKING**:
   - If page contains answer text but NO question number → This is ANSWER CONTINUATION
   - Analyze content context to determine which question this continues (policy area, constitutional topic, etc.)
   - MANDATORY: Every answer must have "linked_to_question" populated (make intelligent guess based on content)
   - Look for content clues: same policy area, similar constitutional themes, continuation phrases

**3. CONTENT QUALITY MARKERS** (Identify these UPSC-specific indicators):
   - **Policy Analysis Depth**: Mentions of implementation challenges, multi-stakeholder approach
   - **Constitutional Knowledge**: Accurate article references, landmark case citations
   - **Current Affairs Integration**: Recent developments, committee reports, government initiatives
   - **Balanced Perspective**: Pros/cons analysis, multiple viewpoints consideration
   - **Solution-Oriented Approach**: Way forward suggestions, policy recommendations

📋 **RESPOND IN EXACT JSON FORMAT**:
{
    "page_number": NUMBER,
    "has_questions": true/false,
    "has_answers": true/false,
    "questions_found": [
        {
            "question_number": NUMBER,
            "question_text": "COMPLETE_QUESTION_INCLUDING_ALL_SUBPARTS_AND_INSTRUCTIONS",
            "word_limit": NUMBER,
            "marks": NUMBER,
            "confidence": "high/medium/low",
            "upsc_topic_area": "polity/economics/society/geography/international_relations/current_affairs/ethics",
            "question_type": "analytical/descriptive/compare_contrast/case_study/evaluate",
            "handwriting_quality": "clear/moderate/difficult"
        }
    ],
    "answers_found": [
        {
            "question_number": NUMBER_OR_NULL_IF_CONTINUATION,
            "answer_text": "COMPLETE_HANDWRITTEN_TEXT_WITH_DETAILED_VISUAL_ELEMENT_DESCRIPTIONS",
            "linked_to_question": ALWAYS_POPULATE_THIS_FIELD_EVEN_IF_GUESS,
            "is_continuation": true/false,
            "has_diagrams": true/false,
            "visual_elements": ["table", "flowchart", "map", "timeline", "organizational_chart", "mind_map", "graph", "bullet_points"],
            "upsc_content_markers": ["constitutional_articles", "government_schemes", "current_affairs", "policy_analysis", "international_agreements", "case_studies"],
            "content_quality_indicators": ["analytical_depth", "examples_provided", "current_affairs_integration", "balanced_perspective", "solution_oriented"],
            "handwriting_quality": "clear/moderate/difficult", 
            "estimated_word_count": NUMBER,
            "confidence": "high/medium/low",
            "page_position": "top/middle/bottom",
            "upsc_topic_area": "polity/economics/society/geography/international_relations/current_affairs"
        }
    ],
    "page_analysis": {
        "content_type": "questions/answers/mixed/instructions/blank",
        "visual_complexity": "simple/moderate/complex",
        "upsc_content_quality": "excellent/good/average/poor",
        "handwriting_assessment": "Overall readability assessment",
        "academic_rigor": "high/medium/low",
        "upsc_indicators": ["constitutional_knowledge", "policy_awareness", "current_affairs", "analytical_thinking", "structured_presentation"],
        "notes": "Specific observations about UPSC answer quality, presentation style, and content depth"
    }
}

🎯 **MANDATORY REQUIREMENTS**:
1. **ANSWER LINKING**: Every answer MUST have "linked_to_question" populated (analyze content if unclear)
2. **Visual Integration**: Describe ALL visual elements as part of answer text for complete evaluation  
3. **UPSC Specificity**: Extract exact policy names, constitutional articles, scheme details, current affairs
4. **Continuation Handling**: For answers without question numbers, analyze content topic and intelligently link
5. **Complete Extraction**: Extract ALL readable handwritten content - missing content impacts evaluation

**SPECIAL INSTRUCTIONS FOR CONTINUATION PAGES**:
- If answer text exists but no question number visible, examine the content closely
- Look for policy continuity, constitutional themes, or topic consistency with previous pages
- Make intelligent linking based on subject matter (e.g., Article 356 content → governance question)
- Populate "linked_to_question" with your best analysis-based guess"""

        try:
            # Create message for vision API
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": vision_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{page_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Use vision chat for analysis with correct model
            response = await self.llm_service.vision_chat(
                messages=messages,
                model="gpt-4.1-mini",  # Use the same model as regular chat for Walmart Gateway
                temperature=0.1,
                max_tokens=6000  # Increased from 2000 to 6000 for comprehensive vision analysis
            )
            
            # Parse JSON response
            try:
                analysis = json.loads(response)
                analysis["page_number"] = page_num
                return analysis
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for page {page_num}, using fallback")
                return {
                    "page_number": page_num,
                    "has_questions": False,
                    "has_answers": False,
                    "questions_found": [],
                    "answers_found": [],
                    "page_analysis": {"content_type": "unknown", "notes": "JSON parsing failed"}
                }
                
        except Exception as e:
            logger.error(f"Error analyzing page {page_num}: {e}")
            return {
                "page_number": page_num,
                "has_questions": False,
                "has_answers": False,
                "questions_found": [],
                "answers_found": [],
                "page_analysis": {"content_type": "error", "notes": f"Analysis failed: {str(e)}"}
            }
    
    def match_questions_to_answers(self, all_analyses: List[Dict]) -> List[Dict]:
        """Enhanced question-answer matching with improved continuation handling"""
        
        # Collect all questions and answers
        questions = {}
        answers = {}
        continuation_answers = []
        last_question_on_page = {}  # Track the last question that appeared on each page
        
        # First pass: collect questions and track page context
        for analysis in all_analyses:
            page_num = analysis["page_number"]
            
            # Collect questions
            for q in analysis.get("questions_found", []):
                q_num = q.get("question_number")
                if q_num and q_num not in questions:
                    questions[q_num] = q
                    questions[q_num]["source_page"] = page_num
                    last_question_on_page[page_num] = q_num
            
            # If no questions on this page, inherit from previous page context
            if not analysis.get("questions_found") and page_num > 1:
                prev_page = page_num - 1
                while prev_page >= 1 and prev_page not in last_question_on_page:
                    prev_page -= 1
                if prev_page in last_question_on_page:
                    last_question_on_page[page_num] = last_question_on_page[prev_page]
        
        # Second pass: collect and properly link answers
        current_question_context = None  # Track current question being answered
        
        for analysis in all_analyses:
            page_num = analysis["page_number"]
            
            for a in analysis.get("answers_found", []):
                a_num = a.get("question_number")
                a["source_page"] = page_num
                
                # Case 1: Answer has explicit question number
                if a_num:
                    if a_num not in answers:
                        answers[a_num] = []
                    a["linked_to_question"] = a_num
                    a["is_continuation"] = False
                    answers[a_num].append(a)
                    current_question_context = a_num  # Update context
                
                # Case 2: Answer without question number (continuation) - Enhanced Intelligent Linking
                else:
                    linked_question = a.get("linked_to_question")
                    
                    # Enhanced Strategy 1: Use previous page question (most common pattern)
                    if not linked_question and page_num - 1 in last_question_on_page:
                        linked_question = last_question_on_page[page_num - 1]
                        a["continuation_context"] = "Previous page question"
                    
                    # Enhanced Strategy 2: Look for nearest previous question within reasonable range
                    elif not linked_question:
                        for offset in range(2, 6):  # Check up to 5 pages back
                            if page_num - offset in last_question_on_page:
                                linked_question = last_question_on_page[page_num - offset]
                                a["continuation_context"] = f"Nearest question {offset} pages back"
                                break
                    
                    # Strategy 3: Content-based intelligent linking
                    if not linked_question:
                        answer_text = a.get("answer_text", "").lower()
                        
                        # UPSC topic-based linking
                        if any(word in answer_text for word in ['article', 'constitution', 'federal', 'amendment']):
                            # Find polity-related question (usually Q1-Q3)
                            for q_num in sorted(questions.keys()):
                                if q_num <= 3:  # Early questions often polity
                                    linked_question = q_num
                                    a["continuation_context"] = "Content-based polity linking"
                                    break
                        elif any(word in answer_text for word in ['enforcement', 'investigation', 'money', 'directorate']):
                            linked_question = 2  # Likely ED-related question
                            a["continuation_context"] = "Content-based ED linking"
                        elif any(word in answer_text for word in ['tribunal', 'court', 'judicial']):
                            # Find judiciary-related question
                            for q_num in sorted(questions.keys()):
                                linked_question = q_num
                                a["continuation_context"] = "Content-based judiciary linking"
                                break
                    
                    # Strategy 4: Use current question context
                    if not linked_question and current_question_context:
                        linked_question = current_question_context
                        a["continuation_context"] = "Current question context"
                    
                    # Strategy 5: Use most recent question (fallback)
                    if not linked_question and questions:
                        linked_question = max(questions.keys())
                        a["continuation_context"] = "Most recent question fallback"
                    
                    if linked_question:
                        if linked_question not in answers:
                            answers[linked_question] = []
                        
                        a["linked_to_question"] = linked_question
                        a["is_continuation"] = True
                        a["continuation_context"] = f"Linked to Q{linked_question} (context-aware linking)"
                        answers[linked_question].append(a)
                        
                        # Don't update current_question_context for continuations
                        # This ensures we keep linking to the same question
                    else:
                        # Fallback: store for later processing
                        continuation_answers.append(a)
        
        # Enhanced intelligent linking for unlinked answers (fixes missing continuation pages)
        fixed_count = 0
        questions_by_page = {}
        
        # Create page-to-question mapping
        for analysis in all_analyses:
            page_num = analysis["page_number"]
            for q in analysis.get("questions_found", []):
                q_num = q.get("question_number")
                if q_num:
                    questions_by_page[page_num] = q_num
        
        for cont_answer in continuation_answers:
            page_num = cont_answer.get('source_page', 0)
            linked_question = None
            
            # Strategy 1: Check if previous page has a question
            if page_num - 1 in questions_by_page:
                linked_question = questions_by_page[page_num - 1]
                cont_answer["continuation_context"] = "Previous page question"
            
            # Strategy 2: Look for the nearest previous question
            elif not linked_question:
                for offset in range(2, 10):  # Check up to 10 pages back
                    if page_num - offset in questions_by_page:
                        linked_question = questions_by_page[page_num - offset]
                        cont_answer["continuation_context"] = f"Nearest question {offset} pages back"
                        break
            
            # Strategy 3: Content-based matching (fallback)
            if not linked_question:
                answer_text = cont_answer.get('answer_text', '').lower()
                
                # Simple keyword matching for UPSC topics
                if any(word in answer_text for word in ['article', 'constitution', 'federal']):
                    linked_question = 1  # Likely polity
                    cont_answer["continuation_context"] = "Content-based polity linking"
                elif any(word in answer_text for word in ['enforcement', 'investigation', 'money']):
                    linked_question = 2  # Likely ED topic
                    cont_answer["continuation_context"] = "Content-based ED linking"
                elif questions:  # Last resort: most recent question
                    recent_q_pages = sorted([p for p in questions_by_page.keys() if p <= page_num], reverse=True)
                    if recent_q_pages:
                        linked_question = questions_by_page[recent_q_pages[0]]
                        cont_answer["continuation_context"] = "Most recent question fallback"
            
            if linked_question:
                if linked_question not in answers:
                    answers[linked_question] = []
                
                cont_answer["linked_to_question"] = linked_question
                cont_answer["is_continuation"] = True
                answers[linked_question].append(cont_answer)
                fixed_count += 1
            else:
                logger.warning(f"Could not link answer on page {page_num} to any question")
        
        logger.info(f"Enhanced linking: Fixed {fixed_count} unlinked continuation answers")
        
        # Create final matched question-answer pairs
        matched_qa = []
        
        for q_num in sorted(questions.keys()):
            question = questions[q_num]
            question_answers = answers.get(q_num, [])
            
            # Sort answers by page number for proper sequential order
            question_answers.sort(key=lambda x: x["source_page"])
            
            # Combine multi-page answers
            combined_answer = ""
            visual_elements = set()
            handwriting_quality = "moderate"
            source_pages = []
            upsc_content_markers = set()
            content_quality_indicators = set()
            
            if question_answers:
                answer_parts = []
                
                for i, ans in enumerate(question_answers):
                    answer_text = ans["answer_text"]
                    
                    # Ensure proper linking for all answer parts
                    ans["linked_to_question"] = q_num
                    
                    if ans.get("is_continuation"):
                        # Mark continuation clearly
                        if i == 0:
                            answer_parts.append(answer_text)
                        else:
                            answer_parts.append(f"\n[Continued on page {ans['source_page']}] {answer_text}")
                    else:
                        answer_parts.append(answer_text)
                    
                    # Aggregate metadata
                    visual_elements.update(ans.get("visual_elements", []))
                    upsc_content_markers.update(ans.get("upsc_content_markers", []))
                    content_quality_indicators.update(ans.get("content_quality_indicators", []))
                    
                    if i == 0:  # Use first answer's handwriting quality as primary
                        handwriting_quality = ans.get("handwriting_quality", "moderate")
                    
                    source_pages.append(ans["source_page"])
                
                combined_answer = " ".join(answer_parts)
            
            # Create comprehensive question-answer object
            matched_qa.append({
                "question_number": q_num,
                "question_text": question["question_text"],
                "word_limit": question.get("word_limit", 150),
                "marks": question.get("marks", 10),
                "student_answer": combined_answer,
                "handwriting_quality": handwriting_quality,
                "question_confidence": question.get("confidence", "medium"),
                "upsc_topic_area": question.get("upsc_topic_area", "general"),
                "question_type": question.get("question_type", "analytical"),
                
                # Visual and content analysis
                "visual_elements": list(visual_elements),
                "upsc_content_markers": list(upsc_content_markers),
                "content_quality_indicators": list(content_quality_indicators),
                "has_diagrams": len(visual_elements) > 0,
                
                # Source tracking
                "source_pages": {
                    "question": question["source_page"],
                    "answers": source_pages
                },
                "answer_span_pages": len(source_pages),
                
                # Processing metadata
                "processing_notes": f"Q{q_num}: {len(question_answers)} answer parts across {len(source_pages)} pages",
                "linked_answers_details": [
                    {
                        "page": ans["source_page"],
                        "linked_to_question": ans["linked_to_question"],
                        "is_continuation": ans.get("is_continuation", False),
                        "confidence": ans.get("confidence", "medium"),
                        "visual_count": len(ans.get("visual_elements", []))
                    } for ans in question_answers
                ]
            })
        
        # Log linking summary for debugging
        logger.info(f"Question-Answer Linking Summary:")
        for qa in matched_qa:
            logger.info(f"Q{qa['question_number']}: {qa['answer_span_pages']} pages, {len(qa['visual_elements'])} visual elements")
        
        return matched_qa
    
    async def extract_questions_only(self, file_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Vision-only PDF processing - extracts questions without comprehensive analysis
        Used by LangGraph workflow to prevent duplicate evaluation
        
        Returns structured data with questions only, no evaluations
        """
        self.processing_start_time = datetime.now()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")
        
        # Open PDF and get basic info
        doc = fitz.open(file_path)
        self.total_pages = len(doc)
        pdf_filename = os.path.basename(file_path)
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Initialize progress tracker
        progress_tracker = ProgressTracker(self.total_pages, progress_callback)
        estimated_minutes = progress_tracker.estimate_total_time()
        
        # Log initial setup
        logger.info(f"📄 VISION-ONLY: Starting processing: {pdf_filename} ({self.total_pages} pages, {file_size_mb:.1f} MB)")
        await progress_tracker.update_progress("initializing", details=f"{pdf_filename} - Vision extraction only")
        
        # Phase 1: Process each page with vision analysis (NO COMPREHENSIVE EVALUATION)
        page_analyses = []
        questions_found = 0
        answers_found = 0
        
        for page_num in range(self.total_pages):
            try:
                current_page = page_num + 1
                page = doc[page_num]
                
                await progress_tracker.update_progress("page_processing", current_page=current_page, 
                                                details=f"Converting page {current_page} to image")
                
                # Convert page to image
                page_image = self.convert_page_to_image(page)
                
                if page_image:
                    await progress_tracker.update_progress("page_processing", current_page=current_page,
                                                   details=f"Analyzing page {current_page} with Vision AI")
                    
                    # Analyze with vision LLM (only for question/answer detection)
                    analysis = await self.analyze_page_with_vision(page_image, current_page)
                    page_analyses.append(analysis)
                    
                    # Count content found
                    page_questions = len(analysis.get("questions_found", []))
                    page_answers = len(analysis.get("answers_found", []))
                    questions_found += page_questions
                    answers_found += page_answers
                    
                    # Update progress with findings
                    if page_questions > 0 or page_answers > 0:
                        details = f"Found {page_questions} questions, {page_answers} answers"
                    else:
                        details = "No content detected on this page"
                    
                    await progress_tracker.update_progress("page_processing", current_page=current_page, details=details)
                    
                    # Add delay between pages to prevent rate limiting
                    if current_page < self.total_pages:  # Don't delay after last page
                        await asyncio.sleep(2.0)  # 2 second delay between pages
                    
                else:
                    await progress_tracker.update_progress("page_processing", current_page=current_page,
                                                   details=f"Failed to process page {current_page}")
                    
            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                await progress_tracker.update_progress("page_processing", current_page=current_page,
                                               details=f"Error on page {current_page}: {str(e)[:50]}")
        
        doc.close()
        
        # Phase 2: Extract and consolidate questions (NO EVALUATION)
        await progress_tracker.update_progress("question_extraction", current_page=0,
                                       details="Consolidating questions from all pages")
        
        # Phase 3: Match questions to answers with progress tracking
        await progress_tracker.update_progress("question_extraction", current_page=self.total_pages,
                                       details="Matching questions to answers")
        
        matched_qa = self.match_questions_to_answers(page_analyses)
        total_questions = len(matched_qa)
        total_marks = sum(qa.get("marks", 0) or 0 for qa in matched_qa)
        
        await progress_tracker.update_progress("question_extraction", current_page=self.total_pages,
                                       details=f"Found {total_questions} questions with {total_marks} total marks")
        
        # Phase 4: SKIP COMPREHENSIVE EVALUATION (this prevents duplicate execution)
        logger.info(f"🔧 VISION-ONLY MODE: Skipping comprehensive evaluation - will be handled by LangGraph analysis node")
        
        # Calculate processing time
        processing_time = (datetime.now() - self.processing_start_time).total_seconds()
        
        # Return structured data without evaluations
        final_result = {
            "success": True,
            "pdf_filename": pdf_filename,
            "total_pages": self.total_pages,
            "file_size_mb": round(file_size_mb, 2),
            "processing_time_seconds": round(processing_time, 2),
            
            # Questions data (no evaluations)
            "questions": matched_qa,
            "total_questions_found": total_questions,
            "total_marks": total_marks,
            
            # Processing metadata
            "extraction_method": "Vision-only extraction (no analysis)",
            "processing_timestamp": datetime.now().isoformat(),
            "extraction_summary": {
                "pages_processed": self.total_pages,
                "questions_found": questions_found,
                "answers_found": answers_found,
                "matched_qa_pairs": total_questions,
                "total_marks_available": total_marks
            },
            
            # Technical metadata
            "technical_metadata": {
                "processing_mode": "vision_only",
                "comprehensive_analysis_skipped": True,
                "analysis_will_be_handled_by": "LangGraph analyze_dimensions_node",
                "duplicate_prevention": True
            }
        }
        
        await progress_tracker.update_progress("finalizing", 
                                       details=f"✅ Vision extraction complete! {total_questions} questions found in {round(processing_time/60, 1)} minutes")
        
        logger.info(f"✅ VISION-ONLY extraction completed: {total_questions} questions, {total_marks} marks, {processing_time:.2f}s")
        
        return final_result
    
    async def process_pdf_with_vision(self, file_path: str, progress_callback: Optional[Callable] = None) -> Dict:
        """
        Complete PDF processing pipeline using vision extraction with comprehensive progress tracking
        Returns structured data ready for 13-dimensional evaluation
        """
        self.processing_start_time = datetime.now()
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")
        
        # Open PDF and get basic info
        doc = fitz.open(file_path)
        self.total_pages = len(doc)
        pdf_filename = os.path.basename(file_path)
        file_size_bytes = os.path.getsize(file_path)
        file_size_mb = file_size_bytes / (1024 * 1024)
        
        # Initialize progress tracker
        progress_tracker = ProgressTracker(self.total_pages, self.progress_callback)
        estimated_minutes = progress_tracker.estimate_total_time()
        
        # Log initial setup
        logger.info(f"📄 Starting processing: {pdf_filename} ({self.total_pages} pages, {file_size_mb:.1f} MB)")
        await progress_tracker.update_progress("initializing", details=f"{pdf_filename} - {estimated_minutes} minutes estimated")
        
        # Phase 1: Process each page with vision analysis
        page_analyses = []
        questions_found = 0
        answers_found = 0
        
        for page_num in range(self.total_pages):
            try:
                current_page = page_num + 1
                page = doc[page_num]
                
                await progress_tracker.update_progress("page_processing", current_page=current_page, 
                                                details=f"Converting page {current_page} to image")
                
                # Convert page to image
                page_image = self.convert_page_to_image(page)
                
                if page_image:
                    await progress_tracker.update_progress("page_processing", current_page=current_page,
                                                   details=f"Analyzing page {current_page} with Vision AI")
                    
                    # Analyze with vision LLM
                    analysis = await self.analyze_page_with_vision(page_image, current_page)
                    page_analyses.append(analysis)
                    
                    # Count content found
                    page_questions = len(analysis.get("questions_found", []))
                    page_answers = len(analysis.get("answers_found", []))
                    questions_found += page_questions
                    answers_found += page_answers
                    
                    # Update progress with findings
                    if page_questions > 0 or page_answers > 0:
                        details = f"Found {page_questions} questions, {page_answers} answers"
                    else:
                        details = "No content detected on this page"
                    
                    await progress_tracker.update_progress("page_processing", current_page=current_page, details=details)
                    
                    # Add delay between pages to prevent rate limiting
                    if current_page < self.total_pages:  # Don't delay after last page
                        await asyncio.sleep(2.0)  # 2 second delay between pages
                    
                else:
                    await progress_tracker.update_progress("page_processing", current_page=current_page,
                                                   details=f"Failed to process page {current_page}")
                    
            except Exception as e:
                logger.error(f"Error processing page {current_page}: {e}")
                await progress_tracker.update_progress("page_processing", current_page=current_page,
                                               details=f"Error on page {current_page}: {str(e)[:50]}")
        
        doc.close()
        
        # Phase 2: Extract and consolidate questions
        await progress_tracker.update_progress("question_extraction", current_page=0,
                                       details="Consolidating questions from all pages")
        
        all_questions = []
        all_answers = []
        
        for page_num, analysis in enumerate(page_analyses):
            await progress_tracker.update_progress("question_extraction", current_page=page_num + 1,
                                           details=f"Extracting from page {page_num + 1}")
            
        # Phase 3: Match questions to answers with progress tracking
        await progress_tracker.update_progress("question_extraction", current_page=self.total_pages,
                                       details="Matching questions to answers")
        
        matched_qa = self.match_questions_to_answers(page_analyses)
        total_questions = len(matched_qa)
        total_marks = sum(qa.get("marks", 0) or 0 for qa in matched_qa)
        
        await progress_tracker.update_progress("question_extraction", current_page=self.total_pages,
                                       details=f"Found {total_questions} questions with {total_marks} total marks")
        
        # Phase 4: Comprehensive evaluation of each question
        evaluation_results = []
        
        for idx, qa_data in enumerate(matched_qa):
            current_q = idx + 1
            question_text = qa_data.get("question_text", "")[:50] + "..."
            
            await progress_tracker.update_progress("answer_evaluation", current_question=current_q,
                                           total_questions=total_questions,
                                           details=f"Comprehensive analysis: {question_text}")
            
            try:
                # Perform 13-dimensional comprehensive evaluation (not just basic evaluation)
                question_text = qa_data.get("question_text", "")
                student_answer = qa_data.get("student_answer", "")
                
                # Use the comprehensive 13-dimensional analysis instead of basic evaluation
                # Fix division by zero error when word_limit is None
                word_limit = qa_data.get("word_limit") or 150
                time_limit = (word_limit // 10) if word_limit and word_limit > 0 else 15  # Default to 15 minutes
                
                eval_result = await comprehensive_question_analysis_direct(
                    question=question_text,
                    student_answer=student_answer,
                    exam_context={
                        "marks": qa_data.get("marks", 10),
                        "time_limit": time_limit,
                        "word_limit": word_limit,
                        "exam_type": "UPSC Mains"
                    },
                    llm_service=self.llm_service
                )
                
                # Store result
                evaluation_results.append({
                    "question_number": qa_data.get("question_number"),
                    "evaluation": eval_result,
                    "question_data": qa_data
                })
                
                await progress_tracker.update_progress("answer_evaluation", current_question=current_q,
                                               total_questions=total_questions,
                                               details=f"Completed Q{qa_data.get('question_number', current_q)}")
                
            except Exception as e:
                logger.error(f"Error evaluating question {current_q}: {e}")
                await progress_tracker.update_progress("answer_evaluation", current_question=current_q,
                                               total_questions=total_questions,
                                               details=f"Error evaluating Q{current_q}: {str(e)[:30]}")
        
        # Phase 5: Finalize results
        await progress_tracker.update_progress("finalizing", details="Preparing final evaluation report")
        
        processing_time = (datetime.now() - self.processing_start_time).total_seconds()
        
        # Create comprehensive result
        final_result = {
            "pdf_filename": pdf_filename,
            "total_pages": self.total_pages,
            "total_questions": total_questions,
            "total_marks": total_marks,
            "questions": matched_qa,
            "evaluation_results": evaluation_results,
            "processing_stats": {
                "processing_time_seconds": round(processing_time, 1),
                "processing_time_minutes": round(processing_time / 60, 1),
                "questions_per_page": round(total_questions / self.total_pages, 1) if self.total_pages > 0 else 0,
                "success_rate": len(evaluation_results) / max(total_questions, 1) * 100
            },
            "extraction_summary": {
                "upsc_indicators_detected": sum(
                    len(qa.get("upsc_content_markers", [])) for qa in matched_qa
                ),
                "vision_processing_used": True,
                "generic_patterns_detected": True,
                "handwriting_quality": "good" if total_questions > 0 else "unknown"
            }
        }
        
        await progress_tracker.update_progress("finalizing", 
                                       details=f"✅ Complete! {total_questions} questions processed in {round(processing_time/60, 1)} minutes")
        
        return final_result
    
    async def create_comprehensive_evaluation(self, qa_data: Dict, db: Session, answer_id: int) -> Dict:
        """
        Create comprehensive 13-dimensional evaluation for each extracted question-answer pair
        """
        logger.info("Starting 13-dimensional evaluation process")
        logger.info(f"DEBUG: qa_data keys: {list(qa_data.keys()) if qa_data else 'None'}")
        
        # Handle different data structures - check for questions key first
        questions_list = None
        if qa_data and 'questions' in qa_data:
            questions_list = qa_data['questions']
            logger.info(f"DEBUG: Found {len(questions_list)} questions to evaluate")
        elif qa_data and isinstance(qa_data, dict):
            # Check if qa_data itself contains question data directly
            if any(key in qa_data for key in ['question_text', 'student_answer', 'question_number']):
                # Single question format
                questions_list = [qa_data]
                logger.info(f"DEBUG: Single question format detected")
            elif 'evaluation_results' in qa_data:
                # Extract from evaluation_results structure
                questions_list = []
                for eval_result in qa_data.get('evaluation_results', []):
                    if 'question_data' in eval_result:
                        questions_list.append(eval_result['question_data'])
                logger.info(f"DEBUG: Extracted {len(questions_list)} questions from evaluation_results")
            else:
                logger.error(f"DEBUG: Unrecognized data structure. Available keys: {list(qa_data.keys())}")
        
        if not questions_list:
            logger.error(f"DEBUG: No questions found in any expected format")
            return {
                "pdf_filename": qa_data.get("pdf_filename", "unknown"),
                "total_questions_evaluated": 0,
                "total_score": "0/0",
                "score_percentage": 0,
                "evaluation_method": "Vision Extraction + 13-Dimensional Analysis",
                "evaluation_timestamp": datetime.now().isoformat(),
                "question_evaluations": [],
                "extraction_metadata": qa_data
            }
        
        evaluation_results = []
        total_score = 0.0  # Initialize as float to avoid type issues
        total_max_score = 0.0  # Initialize as float to avoid type issues
        
        # Create progress tracker for evaluation
        progress_tracker = ProgressTracker(len(questions_list), self.progress_callback)
        await progress_tracker.update_progress("answer_evaluation", current_question=0, 
                                               total_questions=len(questions_list),
                                               details="Starting comprehensive evaluation")
        
        for idx, qa in enumerate(questions_list):
            current_question = idx + 1
            
            # Handle missing or empty student answer
            student_answer = qa.get("student_answer", "").strip()
            if not student_answer:
                logger.info(f"Skipping question {qa.get('question_number', current_question)} - no answer found")
                await progress_tracker.update_progress("answer_evaluation", current_question=current_question,
                                                       total_questions=len(questions_list),
                                                       details=f"Skipped Q{qa.get('question_number', current_question)} (no answer)")
                continue
            
            try:
                question_text = qa.get("question_text", "")
                logger.info(f"Evaluating Q{qa.get('question_number', current_question)}: {question_text[:100]}...")
                
                await progress_tracker.update_progress("answer_evaluation", current_question=current_question,
                                                       total_questions=len(questions_list),
                                                       details=f"Comprehensive analysis: {question_text[:50]}...")
                
                # Step 1: Comprehensive Question Analysis (13-dimensional)
                # Fix word_limit None issue
                word_limit = qa.get("word_limit") or 150
                time_limit = (word_limit // 10) if word_limit and word_limit > 0 else 15  # Default to 15 minutes
                
                question_num = qa.get('question_number', f'Q{current_question}')
                
                comprehensive_analysis = await comprehensive_question_analysis_direct(
                    question=question_text,
                    student_answer=student_answer,
                    exam_context={
                        "marks": qa.get("marks", 10),
                        "time_limit": time_limit,
                        "word_limit": word_limit,
                        "exam_type": "UPSC Mains"
                    },
                    llm_service=self.llm_service,
                    question_number=question_num  # Pass question number for better logging
                )
                
                # Step 2: Detailed Answer Evaluation
                eval_request = AnswerEvaluationRequest(
                    question=question_text,
                    student_answer=student_answer,
                    exam_context=ExamContext(
                        marks=qa.get("marks", 10),
                        time_limit=time_limit,
                        word_limit=word_limit,
                        exam_type="UPSC Mains"
                    )
                )
                
                answer_evaluation = await evaluate_answer(eval_request, self.llm_service)
                
                # Combine results
                question_evaluation = {
                    "question_number": qa.get("question_number", current_question),
                    "question_text": question_text,
                    "student_answer": student_answer,
                    "word_limit": qa.get("word_limit", 150),
                    "marks": qa.get("marks", 10),
                    "handwriting_quality": qa.get("handwriting_quality", "moderate"),
                    "source_pages": qa.get("source_pages", {"question": 1, "answers": [1]}),
                    
                    # 13-dimensional analysis
                    "comprehensive_analysis": comprehensive_analysis,
                    
                    # Detailed evaluation
                    "answer_evaluation": answer_evaluation,
                    
                    # Processing metadata
                    "evaluation_timestamp": datetime.now().isoformat(),
                    "processing_notes": f"Vision extraction + 13-dimensional evaluation"
                }
                
                # Extract score from comprehensive analysis and add to question evaluation
                max_score = qa.get("marks", 10) or 10  # Default to 10 if marks is None
                current_score = 0.0
                
                # Extract score from comprehensive analysis result
                if comprehensive_analysis and isinstance(comprehensive_analysis, dict):
                    if comprehensive_analysis.get("success") and "analysis" in comprehensive_analysis:
                        analysis_data = comprehensive_analysis["analysis"]
                        if "answer_evaluation" in analysis_data:
                            answer_eval_data = analysis_data["answer_evaluation"]
                            current_score_str = answer_eval_data.get("current_score", "0/10")
                            try:
                                if "/" in str(current_score_str):
                                    current_score = float(str(current_score_str).split("/")[0])
                            except (ValueError, IndexError):
                                current_score = 0.0

                # Add extracted scores to the question evaluation object
                question_evaluation["current_score"] = current_score
                question_evaluation["marks_allocated"] = max_score
                
                evaluation_results.append(question_evaluation)
                
                # Update totals using the already extracted scores
                # Ensure values are not None before addition
                current_score = current_score or 0.0
                max_score = max_score or 0.0
                total_score = (total_score or 0.0) + current_score
                total_max_score = (total_max_score or 0.0) + max_score
                logger.info(f"Score tracking: Q{qa.get('question_number', current_question)} = {current_score}/{max_score}, Total: {total_score}/{total_max_score}")
                
                await progress_tracker.update_progress("answer_evaluation", current_question=current_question,
                                                       total_questions=len(questions_list),
                                                       details=f"Completed Q{qa.get('question_number', current_question)}")
                
                logger.info(f"Completed evaluation for Q{qa.get('question_number', current_question)}")
                
            except Exception as e:
                logger.error(f"Error evaluating question {qa.get('question_number', current_question)}: {e}")
                await progress_tracker.update_progress("answer_evaluation", current_question=current_question,
                                                       total_questions=len(questions_list),
                                                       details=f"Error in Q{qa.get('question_number', current_question)}")
                continue
        
        # Finalize evaluation
        await progress_tracker.update_progress("finalizing", details="Preparing evaluation summary")
        
        # Create overall evaluation summary
        evaluation_summary = {
            "pdf_filename": qa_data.get("pdf_filename", "unknown"),
            "total_questions_evaluated": len(evaluation_results),
            "total_score": total_score,  # Numeric value
            "total_max_score": total_max_score,  # Numeric value
            "total_score_display": f"{total_score}/{total_max_score}",  # String for display
            "score_percentage": round((total_score / total_max_score * 100), 2) if total_max_score > 0 else 0,
            "evaluation_method": "Vision Extraction + 13-Dimensional Analysis",
            "evaluation_timestamp": datetime.now().isoformat(),
            "question_evaluations": evaluation_results,
            "extraction_metadata": qa_data
        }
        
        logger.info(f"13-dimensional evaluation complete: {len(evaluation_results)} questions evaluated")
        
        return evaluation_summary


async def process_vision_pdf_with_evaluation(file_path: str, db: Session, answer_id: int, progress_callback=None) -> Dict:
    """
    Complete end-to-end processing: Vision extraction + 13-dimensional evaluation
    """
    logger.info(f"DEBUG: process_vision_pdf_with_evaluation called with file_path={file_path}, answer_id={answer_id}")
    
    processor = VisionPDFProcessor(progress_callback=progress_callback)
    
    # Step 1: Extract questions and answers using vision (this already includes evaluation)
    logger.info("DEBUG: Starting vision extraction...")
    qa_data = await processor.process_pdf_with_vision(file_path)
    
    logger.info(f"DEBUG: Vision extraction complete. Data structure:")
    logger.info(f"DEBUG: qa_data type: {type(qa_data)}")
    logger.info(f"DEBUG: qa_data keys: {list(qa_data.keys()) if qa_data else 'None'}")
    
    # Debug evaluation_results specifically
    if qa_data and 'evaluation_results' in qa_data:
        eval_results = qa_data['evaluation_results']
        logger.info(f"DEBUG: evaluation_results type: {type(eval_results)}")
        logger.info(f"DEBUG: evaluation_results length: {len(eval_results) if eval_results else 'None/0'}")
        if eval_results:
            logger.info(f"DEBUG: First evaluation result keys: {list(eval_results[0].keys()) if eval_results[0] else 'None'}")
    else:
        logger.info("DEBUG: No 'evaluation_results' key found in qa_data")
    
    # Check if we already have evaluation results from process_pdf_with_vision
    if qa_data and 'evaluation_results' in qa_data and qa_data['evaluation_results']:
        logger.info(f"DEBUG: Found {len(qa_data['evaluation_results'])} existing evaluation results from vision processing")
        
        # Convert the existing evaluation results to the expected format
        question_evaluations = []
        total_score = 0.0  # Initialize as float
        total_max_score = 0.0  # Initialize as float
        
        for eval_result in qa_data['evaluation_results']:
            question_data = eval_result.get('question_data', {})
            evaluation = eval_result.get('evaluation')
            
            # Create the expected evaluation format
            question_evaluation = {
                "question_number": question_data.get("question_number"),
                "question_text": question_data.get("question_text", ""),
                "student_answer": question_data.get("student_answer", ""),
                "word_limit": question_data.get("word_limit", 150),
                "marks": question_data.get("marks", 10),
                "handwriting_quality": question_data.get("handwriting_quality", "moderate"),
                "source_pages": question_data.get("source_pages", {"question": 1, "answers": [1]}),
                
                # Use the existing evaluation
                "answer_evaluation": evaluation,
                
                # Processing metadata
                "evaluation_timestamp": datetime.now().isoformat(),
                "processing_notes": "Vision extraction + evaluation (converted format)"
            }
            
            question_evaluations.append(question_evaluation)
            
            # Update totals - Extract score from comprehensive analysis
            # Initialize with safe defaults
            max_score = question_data.get("marks") or 10
            current_score = 0.0
            
            # Ensure max_score is not None
            if max_score is None:
                max_score = 10
            max_score = float(max_score)
            
            # Extract score from evaluation (which contains comprehensive analysis result)
            if evaluation and isinstance(evaluation, dict):
                if evaluation.get("success") and "analysis" in evaluation:
                    analysis_data = evaluation["analysis"]
                    if "answer_evaluation" in analysis_data:
                        answer_eval_data = analysis_data["answer_evaluation"]
                        current_score_str = answer_eval_data.get("current_score", "0/10")
                        try:
                            if "/" in str(current_score_str):
                                current_score = float(str(current_score_str).split("/")[0])
                        except (ValueError, IndexError):
                            current_score = 0.0
            
            # Ensure values are not None before addition - extra safety
            if current_score is None:
                current_score = 0.0
            if max_score is None:
                max_score = 10.0
            if total_score is None:
                total_score = 0.0
            if total_max_score is None:
                total_max_score = 0.0
                
            # Convert to float explicitly
            current_score = float(current_score)
            max_score = float(max_score) 
            total_score = float(total_score)
            total_max_score = float(total_max_score)
            
            # Now safe to add
            total_score += current_score
            total_max_score += max_score
        
        # Create the final evaluation summary in the expected format
        evaluation_summary = {
            "pdf_filename": qa_data.get("pdf_filename", "unknown"),
            "total_questions_evaluated": len(question_evaluations),
            "total_score": total_score,  # Numeric value
            "total_max_score": total_max_score,  # Numeric value
            "total_score_display": f"{total_score}/{total_max_score}",  # String for display
            "score_percentage": round((total_score / total_max_score * 100), 2) if total_max_score > 0 else 0,
            "evaluation_method": "Vision Extraction + Evaluation (Integrated)",
            "evaluation_timestamp": datetime.now().isoformat(),
            "question_evaluations": question_evaluations,
            "extraction_metadata": qa_data
        }
        
        logger.info(f"DEBUG: Converted evaluation results - {len(question_evaluations)} question evaluations created")
        
        # Debug: Log the final structure before returning
        logger.info(f"DEBUG: FINAL RETURN - evaluation_summary type: {type(evaluation_summary)}")
        logger.info(f"DEBUG: FINAL RETURN - evaluation_summary keys: {list(evaluation_summary.keys())}")
        logger.info(f"DEBUG: FINAL RETURN - question_evaluations count: {len(evaluation_summary.get('question_evaluations', []))}")
        
        # CRITICAL DEBUG: Check if question_evaluations key exists and has data
        if 'question_evaluations' in evaluation_summary:
            logger.info(f"DEBUG: ✅ question_evaluations key EXISTS with {len(evaluation_summary['question_evaluations'])} items")
            
            # Log the structure of the first question evaluation
            if evaluation_summary['question_evaluations']:
                first_qeval = evaluation_summary['question_evaluations'][0]
                logger.info(f"DEBUG: First question_evaluation keys: {list(first_qeval.keys()) if isinstance(first_qeval, dict) else 'Not a dict'}")
                
                # Log the complete evaluation_summary for debugging
                logger.info(f"DEBUG: 🎯 COMPLETE RETURN DATA:")
                logger.info(f"DEBUG: pdf_filename: {evaluation_summary.get('pdf_filename')}")
                logger.info(f"DEBUG: total_questions_evaluated: {evaluation_summary.get('total_questions_evaluated')}")
                logger.info(f"DEBUG: total_score: {evaluation_summary.get('total_score')}")
                logger.info(f"DEBUG: score_percentage: {evaluation_summary.get('score_percentage')}")
                logger.info(f"DEBUG: evaluation_method: {evaluation_summary.get('evaluation_method')}")
                logger.info(f"DEBUG: question_evaluations length: {len(evaluation_summary.get('question_evaluations', []))}")
                
        else:
            logger.error(f"DEBUG: ❌ question_evaluations key is MISSING from evaluation_summary!")
            logger.error(f"DEBUG: Available keys: {list(evaluation_summary.keys())}")
        
        return evaluation_summary
    
    else:
        # Fallback: If no evaluation results, do comprehensive evaluation
        logger.info("DEBUG: No existing evaluation results, starting comprehensive evaluation...")
        if qa_data and 'questions' in qa_data:
            logger.info(f"DEBUG: Found {len(qa_data['questions'])} questions in qa_data")
        
        evaluation_results = await processor.create_comprehensive_evaluation(qa_data, db, answer_id)
        
        logger.info(f"DEBUG: Comprehensive evaluation complete.")
        logger.info(f"DEBUG: evaluation_results type: {type(evaluation_results)}")
        logger.info(f"DEBUG: evaluation_results keys: {list(evaluation_results.keys()) if evaluation_results else 'None'}")
        if evaluation_results and 'question_evaluations' in evaluation_results:
            logger.info(f"DEBUG: Found {len(evaluation_results['question_evaluations'])} question evaluations")
        else:
            logger.error("DEBUG: NO question_evaluations key found in evaluation_results!")
        
        # Debug: Log the final structure before returning  
        if evaluation_results:
            logger.info(f"DEBUG: FINAL FALLBACK RETURN - evaluation_results type: {type(evaluation_results)}")
            logger.info(f"DEBUG: FINAL FALLBACK RETURN - evaluation_results keys: {list(evaluation_results.keys())}")
            if 'question_evaluations' in evaluation_results:
                logger.info(f"DEBUG: FINAL FALLBACK RETURN - question_evaluations count: {len(evaluation_results['question_evaluations'])}")
        
        return evaluation_results
