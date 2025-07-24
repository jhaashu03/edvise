#!/usr/bin/env python3
"""
Vision-based PDF Processor for 13-Dimensional Evaluation System
Integrates vision extraction with comprehensive answer evaluation
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
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

# Import core services
from app.core.llm_service import get_llm_service, LLM
from app.api.llm_endpoints import (
    AnswerEvaluationRequest, ExamContext, evaluate_answer,
    comprehensive_question_analysis_direct
)

logger = logging.getLogger(__name__)

# Utility functions for compatibility with existing code
def create_question_specific_evaluation_request(question_data: dict):
    """Create evaluation request for a specific question from PDF processing"""
    return AnswerEvaluationRequest(
        question=question_data["question_text"],
        student_answer=question_data["student_answer"],
        exam_context=ExamContext(
            marks=question_data["marks"],
            time_limit=int(question_data["marks"] * 1.5),  # 1.5 minutes per mark (as integer)
            word_limit=question_data["marks"] * 20,   # 20 words per mark
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
    Integrated with 13-dimensional evaluation system
    """
    
    def __init__(self):
        self.llm_service = get_llm_service()
        self.extracted_questions = []
        self.extracted_answers = []
        self.evaluation_results = []
        
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

**1. UPSC QUESTIONS** (Look for these exact patterns):
   - **Question Numbers**: "1.", "2.", "3." (NOT "Q1", "Question 1") 
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
   - Complete paragraphs with policy analysis and critical evaluation
   - Government schemes: PM-KISAN, MGNREGA, POSHAN, Digital India, etc.
   - Constitutional references: Article 356, Article 370, Article 14, etc.
   - Legislative acts: RTI Act 2005, SARFAESI Act, Insolvency Code, etc.
   - Current affairs: G20 presidency, COP28, Make in India, Atmanirbhar Bharat
   - International relations: QUAD, BRICS, SCO, Indo-Pacific strategy
   - Economic policies: GST, demonetization, PLI schemes, economic surveys
   - Social issues: gender equality, caste dynamics, urbanization challenges

   **🎨 VISUAL ELEMENTS** (Critical for evaluation):
   - **Flowcharts**: "Shows 4-step process: A→B→C→D with connecting arrows"
   - **Tables**: "3x4 table comparing Central vs State powers with examples"
   - **Maps**: "Hand-drawn India map showing northeastern states with boundaries"
   - **Charts**: "Hierarchical diagram: President→PM→Ministers→Departments"
   - **Diagrams**: "Circular flow showing economic policy cycle"
   - **Timelines**: "1947→1991→2014→2020 showing economic liberalization phases"
   - **Mathematical expressions**: GDP formulas, growth rate calculations

   **🔗 CRITICAL: ANSWER CONTINUATION TRACKING**:
   - If page starts with answer text but NO question number → This is a CONTINUATION
   - Look for previous question context clues in the writing
   - Mark as continuation with best guess of which question it continues
   - EVERY answer must have "linked_to_question" field populated

📋 **RESPOND IN EXACT JSON FORMAT**:
{
    "page_number": NUMBER,
    "has_questions": true/false,
    "has_answers": true/false,
    "questions_found": [
        {
            "question_number": NUMBER,
            "question_text": "COMPLETE_QUESTION_INCLUDING_ALL_SUBPARTS",
            "word_limit": NUMBER,
            "marks": NUMBER,
            "confidence": "high/medium/low",
            "upsc_topic_area": "polity/economics/society/geography/international_relations/current_affairs/ethics",
            "question_type": "analytical/descriptive/compare_contrast/case_study"
        }
    ],
    "answers_found": [
        {
            "question_number": NUMBER_OR_NULL_IF_CONTINUATION,
            "answer_text": "COMPLETE_HANDWRITTEN_TEXT_PLUS_DETAILED_VISUAL_DESCRIPTIONS",
            "has_diagrams": true/false,
            "visual_elements": ["flowchart", "table", "map", "timeline", "organizational_chart", "mind_map", "statistical_chart"],
            "upsc_content_markers": ["scheme_names", "constitutional_refs", "current_affairs", "statistics", "international_agreements", "policy_analysis"],
            "handwriting_quality": "clear/moderate/difficult", 
            "is_continuation": true/false,
            "linked_to_question": NUMBER_ALWAYS_POPULATED,
            "confidence": "high/medium/low",
            "content_quality_indicators": ["analytical_depth", "examples_used", "current_affairs_integration", "balanced_perspective"],
            "page_position": "top/middle/bottom"
        }
    ],
    "page_analysis": {
        "content_type": "questions/answers/mixed/blank",
        "visual_complexity": "simple/moderate/complex",
        "upsc_indicators": ["policy_analysis", "constitutional_knowledge", "current_events", "comparative_study", "case_studies"],
        "handwriting_assessment": "Overall readability and presentation quality",
        "notes": "UPSC-specific observations about content quality, presentation, and academic rigor"
    }
}

🎯 **CRITICAL REQUIREMENTS**:
1. **MANDATORY**: Every answer MUST have "linked_to_question" populated (even if guess)
2. **Visual Integration**: Describe ALL diagrams/charts as part of answer text for complete evaluation
3. **UPSC Specificity**: Extract exact policy names, constitutional articles, current affairs references
4. **Continuation Handling**: If no question number visible, determine which question this continues based on content context
5. **Complete Extraction**: Missing content severely impacts student evaluation - be exhaustive

**SPECIAL INSTRUCTION**: If answer content exists but question number is unclear, analyze the content topic and link to the most relevant question number from context."""

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
            
            # Use vision chat for analysis
            response = await self.llm_service.vision_chat(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
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
                
                # Case 2: Answer without question number (continuation)
                else:
                    # Strategy 1: Use LLM-provided linked_to_question
                    linked_question = a.get("linked_to_question")
                    
                    # Strategy 2: If LLM didn't provide link, use current context
                    if not linked_question and current_question_context:
                        linked_question = current_question_context
                    
                    # Strategy 3: Use page context
                    if not linked_question:
                        linked_question = last_question_on_page.get(page_num)
                    
                    # Strategy 4: Use previous page context
                    if not linked_question and page_num > 1:
                        prev_page = page_num - 1
                        while prev_page >= 1:
                            if prev_page in last_question_on_page:
                                linked_question = last_question_on_page[prev_page]
                                break
                            prev_page -= 1
                    
                    # Strategy 5: Use last available question
                    if not linked_question and questions:
                        linked_question = max(questions.keys())
                    
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
        
        # Handle any remaining unlinked answers
        for cont_answer in continuation_answers:
            # Default to question 1 if it exists, otherwise skip
            if 1 in questions:
                if 1 not in answers:
                    answers[1] = []
                cont_answer["linked_to_question"] = 1
                cont_answer["is_continuation"] = True
                cont_answer["continuation_context"] = "Fallback linking to Q1"
                answers[1].append(cont_answer)
            
            logger.warning(f"Could not link answer on page {cont_answer.get('source_page')} to any question")
        
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
    
    async def process_pdf_with_vision(self, file_path: str) -> Dict:
        """
        Complete PDF processing pipeline using vision extraction
        Returns structured data ready for 13-dimensional evaluation
        """
        logger.info(f"Starting vision-based PDF processing: {file_path}")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")
        
        # Open PDF
        doc = fitz.open(file_path)
        total_pages = len(doc)
        pdf_filename = os.path.basename(file_path)
        
        logger.info(f"Processing {total_pages} pages from {pdf_filename}")
        
        # Process each page with vision analysis
        page_analyses = []
        
        for page_num in range(total_pages):
            try:
                page = doc[page_num]
                logger.info(f"Processing page {page_num + 1}/{total_pages}")
                
                # Convert page to image
                page_image = self.convert_page_to_image(page)
                
                if page_image:
                    # Analyze with vision LLM
                    analysis = await self.analyze_page_with_vision(page_image, page_num + 1)
                    page_analyses.append(analysis)
                else:
                    logger.warning(f"Failed to convert page {page_num + 1} to image")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error processing page {page_num + 1}: {e}")
                continue
        
        doc.close()
        
        # Match questions to answers
        matched_qa = self.match_questions_to_answers(page_analyses)
        
        # Calculate totals
        total_questions = len(matched_qa)
        total_marks = sum(qa.get("marks", 0) for qa in matched_qa)
        
        # Create summary
        extraction_summary = {
            "pdf_filename": pdf_filename,
            "pdf_path": file_path,
            "total_pages_processed": len(page_analyses),
            "total_questions_found": total_questions,
            "total_answers_found": len([qa for qa in matched_qa if qa["student_answer"].strip()]),
            "total_marks": total_marks,
            "extraction_method": "Vision-based LLM Analysis",
            "extraction_timestamp": datetime.now().isoformat(),
            "questions": matched_qa,
            "page_analyses": page_analyses
        }
        
        logger.info(f"Vision extraction complete: {total_questions} questions, {total_marks} marks")
        
        return extraction_summary
    
    async def create_comprehensive_evaluation(self, qa_data: Dict, db: Session, answer_id: int) -> Dict:
        """
        Create comprehensive 13-dimensional evaluation for each extracted question-answer pair
        """
        logger.info("Starting 13-dimensional evaluation process")
        
        evaluation_results = []
        total_score = 0
        total_max_score = 0
        
        for qa in qa_data["questions"]:
            if not qa["student_answer"].strip():
                logger.info(f"Skipping question {qa['question_number']} - no answer found")
                continue
            
            try:
                logger.info(f"Evaluating Q{qa['question_number']}: {qa['question_text'][:100]}...")
                
                # Step 1: Comprehensive Question Analysis (13-dimensional)
                comprehensive_analysis = await comprehensive_question_analysis_direct(
                    question=qa["question_text"],
                    student_answer=qa["student_answer"],
                    exam_context={
                        "marks": qa["marks"],
                        "time_limit": qa["word_limit"] // 10,  # Rough estimate: 10 words per minute
                        "word_limit": qa["word_limit"],
                        "exam_type": "UPSC Mains"
                    },
                    llm_service=self.llm_service
                )
                
                # Step 2: Detailed Answer Evaluation
                eval_request = AnswerEvaluationRequest(
                    question=qa["question_text"],
                    student_answer=qa["student_answer"],
                    exam_context=ExamContext(
                        marks=qa["marks"],
                        time_limit=qa["word_limit"] // 10,
                        word_limit=qa["word_limit"],
                        exam_type="UPSC Mains"
                    )
                )
                
                answer_evaluation = await evaluate_answer(eval_request, self.llm_service)
                
                # Combine results
                question_evaluation = {
                    "question_number": qa["question_number"],
                    "question_text": qa["question_text"],
                    "student_answer": qa["student_answer"],
                    "word_limit": qa["word_limit"],
                    "marks": qa["marks"],
                    "handwriting_quality": qa["handwriting_quality"],
                    "source_pages": qa["source_pages"],
                    
                    # 13-dimensional analysis
                    "comprehensive_analysis": comprehensive_analysis,
                    
                    # Detailed evaluation
                    "answer_evaluation": answer_evaluation,
                    
                    # Processing metadata
                    "evaluation_timestamp": datetime.now().isoformat(),
                    "processing_notes": f"Vision extraction + 13-dimensional evaluation"
                }
                
                evaluation_results.append(question_evaluation)
                
                # Update totals
                if hasattr(answer_evaluation, 'scores'):
                    current_score = getattr(answer_evaluation.scores, 'current', '0')
                    max_score = qa["marks"]
                    
                    # Extract numeric score (simple parsing)
                    try:
                        if '/' in str(current_score):
                            score_part = str(current_score).split('/')[0]
                            total_score += float(score_part)
                        total_max_score += max_score
                    except:
                        pass
                
                logger.info(f"Completed evaluation for Q{qa['question_number']}")
                
            except Exception as e:
                logger.error(f"Error evaluating question {qa['question_number']}: {e}")
                continue
        
        # Create overall evaluation summary
        evaluation_summary = {
            "pdf_filename": qa_data["pdf_filename"],
            "total_questions_evaluated": len(evaluation_results),
            "total_score": f"{total_score}/{total_max_score}",
            "score_percentage": round((total_score / total_max_score * 100), 2) if total_max_score > 0 else 0,
            "evaluation_method": "Vision Extraction + 13-Dimensional Analysis",
            "evaluation_timestamp": datetime.now().isoformat(),
            "question_evaluations": evaluation_results,
            "extraction_metadata": qa_data
        }
        
        logger.info(f"13-dimensional evaluation complete: {len(evaluation_results)} questions evaluated")
        
        return evaluation_summary


async def process_vision_pdf_with_evaluation(file_path: str, db: Session, answer_id: int) -> Dict:
    """
    Complete end-to-end processing: Vision extraction + 13-dimensional evaluation
    """
    processor = VisionPDFProcessor()
    
    # Step 1: Extract questions and answers using vision
    qa_data = await processor.process_pdf_with_vision(file_path)
    
    # Step 2: Create comprehensive evaluations
    evaluation_results = await processor.create_comprehensive_evaluation(qa_data, db, answer_id)
    
    return evaluation_results
